from typing import Optional, List
from datetime import datetime, timedelta
import json
import logging
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.llm import get_model
from app.agent.service import AgentService
from app.message.service import MessageService
from app.chat.service import ChatService
from app.background_mgr.service import TaskProgressTracker
from .models import UserJournal
from .schemas import JournalCreate, JournalAnalysis
from .repository import JournalRepository

logger = logging.getLogger(__name__)


JOURNAL_ANALYSIS_PROMPT = """
Analyze the following conversation and create a comprehensive journal entry.

Conversation History:
{conversation_history}

Generate a structured analysis including:

1. SUMMARY (2-3 sentences)
   - What was discussed
   - What was accomplished
   - Key outcomes

2. PSYCHOANALYSIS
   - User's apparent goals and motivations
   - Emotional tone (professional, frustrated, excited, etc.)
   - Confidence level (seeking guidance vs. collaborative)
   - Decision-making style

3. INTERACTION PATTERNS
   - Communication style (concise, detailed, technical, casual)
   - Preferred response format (code examples, explanations, step-by-step)
   - Question patterns (exploratory, specific, troubleshooting)
   - Follow-up behavior

4. TECHNICAL PROFILE
   - Domain expertise demonstrated
   - Technical level (beginner, intermediate, advanced)
   - Tools/technologies mentioned
   - Learning style

5. TOPICS & THEMES
   - Primary topics discussed
   - Recurring themes across conversations
   - Areas of interest

6. PREFERENCES
   - Response length preference
   - Level of detail desired
   - Examples vs. theory
   - Proactive suggestions vs. direct answers

CRITICAL: You MUST respond with ONLY a valid JSON object. Do not include any markdown formatting,
code blocks, or explanatory text. Start your response with {{ and end with }}.

Required JSON structure (use this exact format):
{{
  "summary": "string - 2-3 sentence summary",
  "psychoanalysis": {{
    "goals": "string",
    "emotional_tone": "string",
    "confidence_level": "string",
    "decision_making": "string"
  }},
  "interaction_patterns": {{
    "communication_style": "string",
    "response_format": "string",
    "question_patterns": "string",
    "follow_up_behavior": "string"
  }},
  "technical_profile": {{
    "expertise_areas": "string",
    "technical_level": "string",
    "tools_mentioned": "string",
    "learning_style": "string"
  }},
  "topics": {{
    "primary_topics": "string",
    "recurring_themes": "string",
    "interests": "string"
  }},
  "preferences": {{
    "response_length": "string",
    "detail_level": "string",
    "examples_vs_theory": "string",
    "suggestion_style": "string"
  }}
}}
"""


async def generate_journal_background_task(
    chat_id: str,
    owner_email: str,
    bg_tracker: Optional[TaskProgressTracker] = None
) -> None:
    """
    Background task wrapper for generating journal entries.
    This is called by the background task manager when a journal entry should be generated.
    
    Args:
        chat_id: The chat ID to generate journal for
        owner_email: The owner's email
        bg_tracker: Optional progress tracker from background task manager
    """
    from app.db import get_db_session_ctxmgr
    
    try:
        if bg_tracker:
            await bg_tracker.start(total=1, message="Starting journal generation")
        
        logger.info(f"Starting journal generation for chat {chat_id}")
        
        async with get_db_session_ctxmgr() as db:
            journal_service = JournalService()
            journal = await journal_service.generate_and_store_journal(
                db, chat_id, owner_email, vault_key=""
            )
            
            if journal:
                # Access summary while session is still open
                summary_preview = journal.summary[:100] if journal.summary else "Journal created"
                journal_id = str(journal.journal_id)
                
                if bg_tracker:
                    await bg_tracker.complete(message=f"Journal entry created: {summary_preview}")
                
                logger.info(f"Successfully generated journal {journal_id} for chat {chat_id}")
            else:
                # FIXED: Don't log success when journal is None
                logger.warning(f"Journal generation returned None for chat {chat_id}")
                if bg_tracker:
                    await bg_tracker.fail("Journal generation failed: No analysis generated")
        
    except Exception as e:
        logger.error(f"Failed to generate journal for chat {chat_id}: {e}", exc_info=True)
        if bg_tracker:
            await bg_tracker.fail(f"Journal generation failed: {str(e)}")
        raise


class JournalService:
    def __init__(
        self,
        journal_repo: Optional[JournalRepository] = None,
        message_service: Optional[MessageService] = None,
        chat_service: Optional[ChatService] = None,
    ):
        from app.attachment.service import AttachmentService
        
        self.journal_repo = journal_repo or JournalRepository()
        self.chat_service = chat_service or ChatService()
        # MessageService requires chat_service and attachment_service
        self.message_service = message_service or MessageService(
            chat_service=self.chat_service,
            attachment_service=AttachmentService()
        )
    
    async def detect_conversation_transition(
        self,
        db: AsyncSession,
        chat_id: str,
        email: str,
        vault_key: str = ""
    ) -> bool:
        """
        Detect if conversation has concluded or transitioned.
        Triggers:
        - Extended inactivity (>30 mins)
        - User says goodbye/thanks
        - Topic shift detected
        - Minimum message threshold met
        """
        try:
            # Get chat info
            chat = await self.chat_service.get_chat_if_authorized(
                db, chat_id, email, vault_key != ""
            )
            
            # Check if minimum messages threshold met
            messages = await self.message_service.get_chat_history(
                db, chat_id, email, vault_key
            )
            
            if len(messages) < 5:  # Configurable threshold
                return False
            
            # Check for existing journal for this chat
            existing_journal = await self.journal_repo.get_by_chat_id(db, chat_id)
            if existing_journal:
                # Already has journal, don't create another
                return False
            
            # Check inactivity
            time_since_last_message = datetime.utcnow() - chat.last_message_at
            if time_since_last_message > timedelta(minutes=30):
                logger.info(f"Conversation transition detected for chat {chat_id}: inactivity")
                return True
            
            # TODO: Add more sophisticated detection:
            # - Analyze last message for goodbye/thanks patterns
            # - Detect topic shifts
            # - User explicit request for summary
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting conversation transition: {e}")
            return False
    
    def _clean_llm_content(self, content: str) -> str:
        """
        Clean LLM response content by removing markdown code blocks and extra whitespace.
        
        Args:
            content: Raw content from LLM
            
        Returns:
            Cleaned content string
        """
        if not content:
            return content
            
        content = content.strip()
        
        # Remove markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
            
        if content.endswith("```"):
            content = content[:-3]
            
        return content.strip()
    
    def _validate_json_structure(self, content: str) -> bool:
        """
        Validate that content looks like valid JSON before attempting to parse.
        
        Args:
            content: Content to validate
            
        Returns:
            True if content appears to be valid JSON structure
        """
        if not content:
            return False
            
        content = content.strip()
        
        # Basic structural check
        if not (content.startswith("{") and content.endswith("}")):
            return False
            
        # Check for balanced braces (simple check)
        open_count = content.count("{")
        close_count = content.count("}")
        
        return open_count == close_count
    
    async def generate_journal_entry(
        self,
        db: AsyncSession,
        chat_id: str,
        email: str,
        vault_key: str = ""
    ) -> Optional[JournalAnalysis]:
        """
        Generate comprehensive journal entry for a conversation.
        Uses LLM to analyze conversation history with retry logic and enhanced error handling.
        
        CHANGED: Now uses the main chat model (get_model(efficient=False)) instead of 
        the efficient model for better quality journal generation.
        """
        max_retries = 3
        retry_delay = 1.0  # seconds
        
        try:
            # Get conversation history from LangGraph checkpoint
            messages = await self._get_messages_for_chat(db, chat_id, email, vault_key)
            
            if not messages:
                logger.warning(f"No messages found for chat {chat_id}")
                return None
            
            # Format conversation history for analysis
            conversation_text = self._format_conversation_for_analysis(messages)
            
            # Validate conversation text
            if not conversation_text or len(conversation_text.strip()) < 10:
                logger.warning(f"Conversation text too short or empty for chat {chat_id}")
                return None
            
            # Retry loop for LLM calls
            for attempt in range(max_retries):
                try:
                    logger.debug(f"Attempting LLM call for chat {chat_id}, attempt {attempt + 1}/{max_retries}")
                    
                    # CHANGED: Use main chat model instead of efficient model
                    # This ensures journal generation uses the same high-quality model as the chat
                    model = get_model(efficient=False)
                    prompt = JOURNAL_ANALYSIS_PROMPT.format(
                        conversation_history=conversation_text
                    )
                    
                    response = await model.ainvoke(prompt)
                    
                    # Extract content with comprehensive error handling
                    content = getattr(response, "content", None)
                    
                    # Log response for debugging
                    logger.debug(f"LLM response type: {type(response)}")
                    logger.debug(f"LLM response content type: {type(content)}")
                    
                    # Handle different content types
                    if isinstance(content, list):
                        content = "".join(
                            part.get("text", "") if isinstance(part, dict) else str(part)
                            for part in content
                        )
                    elif content is None:
                        logger.warning(f"LLM returned None content for chat {chat_id}, attempt {attempt + 1}/{max_retries}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay * (attempt + 1))
                            continue
                        else:
                            logger.error(f"LLM returned None content after {max_retries} attempts for chat {chat_id}")
                            return None
                    elif not isinstance(content, str):
                        content = str(content)
                    
                    # Strict validation of content
                    if not content or not content.strip():
                        logger.warning(f"LLM returned empty/whitespace content for chat {chat_id}, attempt {attempt + 1}/{max_retries}")
                        logger.debug(f"Response object: {response}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay * (attempt + 1))
                            continue
                        else:
                            logger.error(f"LLM returned empty content after {max_retries} attempts")
                            return None
                    
                    # Clean content - remove markdown code blocks if present
                    content = self._clean_llm_content(content)
                    
                    # Validate JSON structure before parsing
                    if not self._validate_json_structure(content):
                        logger.warning(f"Content doesn't look like valid JSON for chat {chat_id}, attempt {attempt + 1}/{max_retries}")
                        logger.debug(f"Content preview: {content[:200]}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay * (attempt + 1))
                            continue
                        else:
                            logger.error(f"Invalid JSON structure after {max_retries} attempts")
                            logger.debug(f"Full content: {content}")
                            return None
                    
                    # Log content for debugging
                    logger.debug(f"Content to parse (first 200 chars): {content[:200]}")
                    
                    # Parse JSON response
                    try:
                        analysis_data = json.loads(content)
                    except json.JSONDecodeError as json_err:
                        logger.warning(f"JSON parse error for chat {chat_id}, attempt {attempt + 1}/{max_retries}: {json_err}")
                        logger.debug(f"Failed content: {content[:500]}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay * (attempt + 1))
                            continue
                        else:
                            logger.error(f"Failed to parse JSON after {max_retries} attempts")
                            logger.debug(f"Full failed content: {content}")
                            raise
                    
                    # Validate required fields
                    required_fields = ["summary", "psychoanalysis", "interaction_patterns", 
                                     "technical_profile", "topics", "preferences"]
                    missing_fields = [f for f in required_fields if f not in analysis_data]
                    if missing_fields:
                        logger.warning(f"Missing required fields {missing_fields} for chat {chat_id}, attempt {attempt + 1}/{max_retries}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay * (attempt + 1))
                            continue
                        else:
                            logger.error(f"Missing fields after {max_retries} attempts: {missing_fields}")
                            return None
                    
                    # Success! Create and return the analysis
                    logger.info(f"Successfully parsed journal analysis for chat {chat_id}")
                    return JournalAnalysis(**analysis_data)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error on attempt {attempt + 1} for chat {chat_id}: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        continue
                    else:
                        logger.error(f"Failed to parse JSON after {max_retries} attempts")
                        return None
                        
                except Exception as e:
                    logger.error(f"Unexpected error on attempt {attempt + 1} for chat {chat_id}: {e}", exc_info=True)
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        continue
                    else:
                        raise
            
            # Should not reach here, but just in case
            logger.error(f"Exhausted all retry attempts for chat {chat_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error generating journal entry: {e}", exc_info=True)
            return None
    
    async def _get_messages_for_chat(
        self,
        db: AsyncSession,
        chat_id: str,
        email: str,
        vault_key: str = ""
    ) -> list:
        """Get messages from LangGraph checkpoint for a chat."""
        from app.attachment.service import AttachmentService
        from sqlalchemy import select
        from app.chat.models import Chat
        from app.message.utils import get_chat_agent_type
        
        # Get chat to determine namespace/agent type
        stmt = select(Chat).where(Chat.chat_id == chat_id)
        result = await db.execute(stmt)
        chat = result.scalar_one_or_none()
        
        if not chat:
            logger.warning(f"Chat {chat_id} not found")
            return []
        
        # Get agent service
        attachment_service = AttachmentService()
        agent_service = AgentService(
            agent_type=get_chat_agent_type(chat.namespace),
            attachment_service=attachment_service
        )
        
        # Get latest checkpoint state
        try:
            state = await agent_service.get_latest_checkpoint(
                db, chat_id, email, vault_key
            )
            return state.values.get("messages", [])
        except Exception as e:
            logger.error(f"Failed to get checkpoint messages for chat {chat_id}: {e}")
            return []
    
    def _format_conversation_for_analysis(self, messages: list) -> str:
        """Format LangGraph messages for analysis"""
        from app.core.utils import extract_lc_msg_content
        
        lines: list[str] = []
        for m in messages:
            # Get role from message type
            msg_type = type(m).__name__
            if "Human" in msg_type:
                role = "USER"
            elif "AI" in msg_type or "Assistant" in msg_type:
                role = "ASSISTANT"
            elif "Tool" in msg_type:
                role = "TOOL"
            else:
                role = "SYSTEM"
            
            # Extract content - returns dict of {index: {type, text/...}}
            content_dict = extract_lc_msg_content(m)
            
            # Convert dict to readable text
            text_parts = []
            for idx in sorted(content_dict.keys()):
                item = content_dict[idx]
                if isinstance(item, dict) and "text" in item:
                    text_parts.append(item["text"])
                elif isinstance(item, dict):
                    # Handle other content types (images, etc)
                    text_parts.append(f"[{item.get('type', 'unknown')}: {item.get('source', 'N/A')}]")
                else:
                    text_parts.append(str(item))
            
            content_str = " ".join(text_parts)
            lines.append(f"{role}: {content_str}")

        return "\n\n".join(lines)
    
    def _extract_text_content(self, content: dict) -> str:
        """Extract text from message content structure"""
        texts = []
        for idx, content_item in content.items():
            if content_item.type == "text" and hasattr(content_item, 'text'):
                texts.append(content_item.text)
        return " ".join(texts)
    
    async def create_journal_entry(
        self,
        db: AsyncSession,
        owner_id: str,
        chat_id: str,
        journal_data: JournalAnalysis,
        conversation_start: Optional[datetime] = None,
        conversation_end: Optional[datetime] = None,
        message_count: Optional[int] = None
    ) -> UserJournal:
        """Store journal entry in database"""
        journal_create = JournalCreate(
            owner_id=owner_id,
            chat_id=chat_id,
            journal_type="conversation",
            summary=journal_data.summary,
            psychoanalysis=journal_data.psychoanalysis,
            interaction_patterns=journal_data.interaction_patterns,
            user_preferences=journal_data.preferences,  # Map preferences correctly
            topics=journal_data.topics,
            sentiment_analysis=None,  # Not in current analysis
            conversation_start=conversation_start,
            conversation_end=conversation_end,
            message_count=message_count
        )
        
        return await self.journal_repo.create_one(db, obj_in=journal_create)
    
    async def get_user_journals(
        self,
        db: AsyncSession,
        owner_id: str,
        limit: int = 50,
        offset: int = 0,
        journal_type: Optional[str] = None
    ) -> List[UserJournal]:
        """Retrieve user's journal entries"""
        return await self.journal_repo.get_by_owner(
            db, owner_id, limit=limit, offset=offset, journal_type=journal_type
        )
    
    async def count_user_journals(
        self,
        db: AsyncSession,
        owner_id: str,
        journal_type: Optional[str] = None
    ) -> int:
        """Count user's journal entries"""
        return await self.journal_repo.count_by_owner(
            db, owner_id, journal_type=journal_type
        )
    
    async def generate_and_store_journal(
        self,
        db: AsyncSession,
        chat_id: str,
        email: str,
        vault_key: str = ""
    ) -> Optional[UserJournal]:
        """
        Complete flow: generate and store journal entry.
        Called as background task after conversation transition.
        """
        try:
            logger.info(f"Generating journal for chat {chat_id}, user {email}")
            
            # Check for existing journal
            from uuid import UUID
            try:
                chat_uuid = UUID(chat_id)
                existing_journal = await self.journal_repo.get_by_chat_id(db, chat_uuid)
                if existing_journal:
                    logger.info(f"Journal already exists for chat {chat_id}")
                    return existing_journal
            except ValueError:
                logger.error(f"Invalid chat_id format: {chat_id}")
                return None
            
            # Generate analysis
            analysis = await self.generate_journal_entry(db, chat_id, email, vault_key)
            if not analysis:
                logger.warning(f"Failed to generate analysis for chat {chat_id}")
                return None
            
            # Get chat metadata
            chat = await self.chat_service.get_chat_if_authorized(
                db, chat_id, email, vault_key != ""
            )
            
            messages = await self._get_messages_for_chat(db, chat_id, email, vault_key)
            
            # Store journal
            journal = await self.create_journal_entry(
                db,
                owner_id=email,
                chat_id=chat_id,
                journal_data=analysis,
                conversation_start=chat.created_at,
                conversation_end=chat.last_message_at,
                message_count=len(messages)
            )
            
            logger.info(f"Journal created successfully: {journal.journal_id}")
            return journal
            
        except Exception as e:
            logger.error(f"Error in generate_and_store_journal: {e}", exc_info=True)
            return None
