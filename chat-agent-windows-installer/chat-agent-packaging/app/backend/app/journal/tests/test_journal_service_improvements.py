"""
Unit tests for journal service improvements
Test the enhanced error handling, retry logic, and content validation
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

# Assuming these imports work in your environment
# from app.journal.service import JournalService
# from app.journal.schemas import JournalAnalysis


class TestJournalServiceErrorHandling:
    """Test suite for journal service error handling improvements"""
    
    @pytest.fixture
    def journal_service(self):
        """Create a JournalService instance for testing"""
        # Mock dependencies
        with patch('app.journal.service.JournalRepository'):
            with patch('app.journal.service.ChatService'):
                with patch('app.journal.service.MessageService'):
                    from app.journal.service import JournalService
                    return JournalService()
    
    @pytest.mark.asyncio
    async def test_clean_llm_content_removes_markdown(self, journal_service):
        """Test that markdown code blocks are properly removed"""
        # Test with ```json wrapper
        content = '```json\n{"key": "value"}\n```'
        cleaned = journal_service._clean_llm_content(content)
        assert cleaned == '{"key": "value"}'
        
        # Test with ``` wrapper
        content = '```\n{"key": "value"}\n```'
        cleaned = journal_service._clean_llm_content(content)
        assert cleaned == '{"key": "value"}'
        
        # Test without wrapper
        content = '{"key": "value"}'
        cleaned = journal_service._clean_llm_content(content)
        assert cleaned == '{"key": "value"}'
        
        # Test with extra whitespace
        content = '  \n  ```json\n{"key": "value"}\n```  \n  '
        cleaned = journal_service._clean_llm_content(content)
        assert cleaned == '{"key": "value"}'
    
    @pytest.mark.asyncio
    async def test_validate_json_structure(self, journal_service):
        """Test JSON structure validation"""
        # Valid JSON structure
        assert journal_service._validate_json_structure('{"key": "value"}') == True
        assert journal_service._validate_json_structure('{"nested": {"key": "value"}}') == True
        
        # Invalid JSON structure
        assert journal_service._validate_json_structure('') == False
        assert journal_service._validate_json_structure('null') == False
        assert journal_service._validate_json_structure('not json') == False
        assert journal_service._validate_json_structure('{"unbalanced": {') == False
        assert journal_service._validate_json_structure('[1, 2, 3]') == False  # Array, not object
    
    @pytest.mark.asyncio
    async def test_generate_journal_entry_with_empty_response(self, journal_service):
        """Test handling of empty LLM response"""
        mock_db = AsyncMock()
        
        # Mock _get_messages_for_chat to return valid messages
        journal_service._get_messages_for_chat = AsyncMock(return_value=[
            Mock(content="Hello", type=Mock(__name__="HumanMessage"))
        ])
        
        # Mock _format_conversation_for_analysis
        journal_service._format_conversation_for_analysis = Mock(
            return_value="USER: Hello"
        )
        
        # Mock LLM to return empty content
        with patch('app.journal.service.get_model') as mock_get_model:
            mock_model = AsyncMock()
            mock_response = Mock()
            mock_response.content = ""  # Empty response
            mock_model.ainvoke = AsyncMock(return_value=mock_response)
            mock_get_model.return_value = mock_model
            
            result = await journal_service.generate_journal_entry(
                mock_db, "test-chat-id", "test@example.com"
            )
            
            # Should return None after retries
            assert result is None
            # Should have tried 3 times
            assert mock_model.ainvoke.call_count == 3
    
    @pytest.mark.asyncio
    async def test_generate_journal_entry_with_none_response(self, journal_service):
        """Test handling of None LLM response"""
        mock_db = AsyncMock()
        
        journal_service._get_messages_for_chat = AsyncMock(return_value=[
            Mock(content="Hello")
        ])
        journal_service._format_conversation_for_analysis = Mock(
            return_value="USER: Hello"
        )
        
        with patch('app.journal.service.get_model') as mock_get_model:
            mock_model = AsyncMock()
            mock_response = Mock()
            mock_response.content = None  # None response
            mock_model.ainvoke = AsyncMock(return_value=mock_response)
            mock_get_model.return_value = mock_model
            
            result = await journal_service.generate_journal_entry(
                mock_db, "test-chat-id", "test@example.com"
            )
            
            assert result is None
            assert mock_model.ainvoke.call_count == 3
    
    @pytest.mark.asyncio
    async def test_generate_journal_entry_with_markdown_wrapped_json(self, journal_service):
        """Test successful parsing of markdown-wrapped JSON"""
        mock_db = AsyncMock()
        
        journal_service._get_messages_for_chat = AsyncMock(return_value=[
            Mock(content="Hello")
        ])
        journal_service._format_conversation_for_analysis = Mock(
            return_value="USER: Hello"
        )
        
        valid_json = json.dumps({
            "summary": "Test summary",
            "psychoanalysis": {
                "goals": "Test goals",
                "emotional_tone": "Professional",
                "confidence_level": "High",
                "decision_making": "Analytical"
            },
            "interaction_patterns": {
                "communication_style": "Direct",
                "response_format": "Detailed",
                "question_patterns": "Specific",
                "follow_up_behavior": "Thorough"
            },
            "technical_profile": {
                "expertise_areas": "Python",
                "technical_level": "Advanced",
                "tools_mentioned": "pytest",
                "learning_style": "Hands-on"
            },
            "topics": {
                "primary_topics": "Testing",
                "recurring_themes": "Quality",
                "interests": "Automation"
            },
            "preferences": {
                "response_length": "Medium",
                "detail_level": "High",
                "examples_vs_theory": "Examples",
                "suggestion_style": "Proactive"
            }
        })
        
        with patch('app.journal.service.get_model') as mock_get_model:
            mock_model = AsyncMock()
            mock_response = Mock()
            # Wrap in markdown code block
            mock_response.content = f"```json\n{valid_json}\n```"
            mock_model.ainvoke = AsyncMock(return_value=mock_response)
            mock_get_model.return_value = mock_model
            
            result = await journal_service.generate_journal_entry(
                mock_db, "test-chat-id", "test@example.com"
            )
            
            # Should successfully parse
            assert result is not None
            assert result.summary == "Test summary"
            # Should only call once (success on first try)
            assert mock_model.ainvoke.call_count == 1
    
    @pytest.mark.asyncio
    async def test_generate_journal_entry_with_malformed_json(self, journal_service):
        """Test handling of malformed JSON"""
        mock_db = AsyncMock()
        
        journal_service._get_messages_for_chat = AsyncMock(return_value=[
            Mock(content="Hello")
        ])
        journal_service._format_conversation_for_analysis = Mock(
            return_value="USER: Hello"
        )
        
        with patch('app.journal.service.get_model') as mock_get_model:
            mock_model = AsyncMock()
            mock_response = Mock()
            mock_response.content = '{"invalid": json}'  # Malformed JSON
            mock_model.ainvoke = AsyncMock(return_value=mock_response)
            mock_get_model.return_value = mock_model
            
            result = await journal_service.generate_journal_entry(
                mock_db, "test-chat-id", "test@example.com"
            )
            
            # Should return None after retries
            assert result is None
            # Should have tried 3 times
            assert mock_model.ainvoke.call_count == 3
    
    @pytest.mark.asyncio
    async def test_generate_journal_entry_with_missing_fields(self, journal_service):
        """Test handling of JSON with missing required fields"""
        mock_db = AsyncMock()
        
        journal_service._get_messages_for_chat = AsyncMock(return_value=[
            Mock(content="Hello")
        ])
        journal_service._format_conversation_for_analysis = Mock(
            return_value="USER: Hello"
        )
        
        # JSON missing required fields
        incomplete_json = json.dumps({
            "summary": "Test summary",
            # Missing other required fields
        })
        
        with patch('app.journal.service.get_model') as mock_get_model:
            mock_model = AsyncMock()
            mock_response = Mock()
            mock_response.content = incomplete_json
            mock_model.ainvoke = AsyncMock(return_value=mock_response)
            mock_get_model.return_value = mock_model
            
            result = await journal_service.generate_journal_entry(
                mock_db, "test-chat-id", "test@example.com"
            )
            
            # Should return None after retries
            assert result is None
            # Should have tried 3 times
            assert mock_model.ainvoke.call_count == 3
    
    @pytest.mark.asyncio
    async def test_generate_journal_entry_retry_succeeds_on_second_attempt(self, journal_service):
        """Test that retry logic succeeds on second attempt"""
        mock_db = AsyncMock()
        
        journal_service._get_messages_for_chat = AsyncMock(return_value=[
            Mock(content="Hello")
        ])
        journal_service._format_conversation_for_analysis = Mock(
            return_value="USER: Hello"
        )
        
        valid_json = json.dumps({
            "summary": "Test summary",
            "psychoanalysis": {"goals": "Test", "emotional_tone": "Test", 
                             "confidence_level": "Test", "decision_making": "Test"},
            "interaction_patterns": {"communication_style": "Test", "response_format": "Test",
                                   "question_patterns": "Test", "follow_up_behavior": "Test"},
            "technical_profile": {"expertise_areas": "Test", "technical_level": "Test",
                                "tools_mentioned": "Test", "learning_style": "Test"},
            "topics": {"primary_topics": "Test", "recurring_themes": "Test", "interests": "Test"},
            "preferences": {"response_length": "Test", "detail_level": "Test",
                          "examples_vs_theory": "Test", "suggestion_style": "Test"}
        })
        
        with patch('app.journal.service.get_model') as mock_get_model:
            mock_model = AsyncMock()
            
            # First call returns empty, second call returns valid JSON
            mock_response_empty = Mock()
            mock_response_empty.content = ""
            
            mock_response_valid = Mock()
            mock_response_valid.content = valid_json
            
            mock_model.ainvoke = AsyncMock(
                side_effect=[mock_response_empty, mock_response_valid]
            )
            mock_get_model.return_value = mock_model
            
            # Mock asyncio.sleep to speed up test
            with patch('asyncio.sleep', new=AsyncMock()):
                result = await journal_service.generate_journal_entry(
                    mock_db, "test-chat-id", "test@example.com"
                )
            
            # Should succeed on second attempt
            assert result is not None
            assert result.summary == "Test summary"
            # Should have tried twice
            assert mock_model.ainvoke.call_count == 2
    
    @pytest.mark.asyncio
    async def test_generate_journal_entry_no_messages(self, journal_service):
        """Test handling when no messages are found"""
        mock_db = AsyncMock()
        
        # Mock to return no messages
        journal_service._get_messages_for_chat = AsyncMock(return_value=[])
        
        result = await journal_service.generate_journal_entry(
            mock_db, "test-chat-id", "test@example.com"
        )
        
        # Should return None immediately without calling LLM
        assert result is None
    
    @pytest.mark.asyncio
    async def test_generate_journal_entry_conversation_too_short(self, journal_service):
        """Test handling when conversation text is too short"""
        mock_db = AsyncMock()
        
        journal_service._get_messages_for_chat = AsyncMock(return_value=[
            Mock(content="Hi")
        ])
        journal_service._format_conversation_for_analysis = Mock(
            return_value="Hi"  # Too short
        )
        
        result = await journal_service.generate_journal_entry(
            mock_db, "test-chat-id", "test@example.com"
        )
        
        # Should return None without calling LLM
        assert result is None


class TestJournalBackgroundTask:
    """Test suite for background task improvements"""
    
    @pytest.mark.asyncio
    async def test_background_task_logs_failure_correctly(self):
        """Test that background task doesn't log success when journal is None"""
        from app.journal.service import generate_journal_background_task
        
        mock_tracker = AsyncMock()
        
        with patch('app.journal.service.get_db_session_ctxmgr') as mock_db_ctx:
            mock_db = AsyncMock()
            mock_db_ctx.return_value.__aenter__.return_value = mock_db
            
            with patch('app.journal.service.JournalService') as mock_service_class:
                mock_service = AsyncMock()
                # Return None to simulate failure
                mock_service.generate_and_store_journal = AsyncMock(return_value=None)
                mock_service_class.return_value = mock_service
                
                await generate_journal_background_task(
                    "test-chat-id",
                    "test@example.com",
                    mock_tracker
                )
                
                # Should call fail, not complete
                mock_tracker.fail.assert_called_once()
                mock_tracker.complete.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_background_task_logs_success_correctly(self):
        """Test that background task logs success when journal is created"""
        from app.journal.service import generate_journal_background_task
        
        mock_tracker = AsyncMock()
        
        with patch('app.journal.service.get_db_session_ctxmgr') as mock_db_ctx:
            mock_db = AsyncMock()
            mock_db_ctx.return_value.__aenter__.return_value = mock_db
            
            with patch('app.journal.service.JournalService') as mock_service_class:
                mock_service = AsyncMock()
                
                # Create a mock journal object
                mock_journal = Mock()
                mock_journal.summary = "Test summary for journal"
                mock_journal.journal_id = "test-journal-id"
                
                mock_service.generate_and_store_journal = AsyncMock(return_value=mock_journal)
                mock_service_class.return_value = mock_service
                
                await generate_journal_background_task(
                    "test-chat-id",
                    "test@example.com",
                    mock_tracker
                )
                
                # Should call complete, not fail
                mock_tracker.complete.assert_called_once()
                mock_tracker.fail.assert_not_called()


# Run tests
if __name__ == "__main__":
    print("To run these tests, execute:")
    print("pytest test_journal_service_improvements.py -v")
    print("\nOr for specific test:")
    print("pytest test_journal_service_improvements.py::TestJournalServiceErrorHandling::test_clean_llm_content_removes_markdown -v")
