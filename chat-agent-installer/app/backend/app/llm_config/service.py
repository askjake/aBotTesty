"""
Business logic for LLM provider management
"""
from typing import List, Optional
import logging

from app.llm_config.repository import LLMProviderRepository
from app.llm_config.models import LLMProviderModel
from app.core.llm.schemas import (
    LLMProviderConfig,
    LLMProviderCreate,
    LLMProviderUpdate,
    LLMProviderResponse,
    LLMProviderTestRequest,
    LLMProviderTestResponse,
    LLMModelConfig
)
from app.core.llm.chat_models import (
    get_provider_registry,
    create_chat_model
)
from app.core.llm.discovery import get_discovery_service

logger = logging.getLogger(__name__)


class LLMProviderService:
    """Service for managing LLM providers"""
    
    def __init__(self, repository: LLMProviderRepository):
        self.repository = repository
        self.registry = get_provider_registry()
        self.discovery = get_discovery_service()
    
    def _db_to_config(self, db_provider: LLMProviderModel) -> LLMProviderConfig:
        """Convert database model to config"""
        return LLMProviderConfig(
            id=db_provider.id,
            name=db_provider.name,
            provider_type=db_provider.provider_type,
            api_key=db_provider.api_key,
            api_base=db_provider.api_base,
            models=[LLMModelConfig(**m) for m in (db_provider.models or [])],
            extra_config=db_provider.extra_config or {},
            is_active=db_provider.is_active,
            is_default=db_provider.is_default,
            created_at=db_provider.created_at.isoformat() if db_provider.created_at else None,
            updated_at=db_provider.updated_at.isoformat() if db_provider.updated_at else None
        )
    
    async def create_provider(self, provider: LLMProviderCreate) -> LLMProviderResponse:
        """Create a new provider"""
        # Create in database
        db_provider = await self.repository.create(provider)
        
        # Register in runtime registry
        config = self._db_to_config(db_provider)
        self.registry.register_provider(config)
        
        # Test availability
        is_available, error = await self.discovery.test_provider(config)
        
        logger.info(f"Created provider: {db_provider.name} (available: {is_available})")
        
        return LLMProviderResponse.from_config(config, is_available=is_available)
    
    async def get_provider(self, provider_id: str) -> Optional[LLMProviderResponse]:
        """Get provider by ID"""
        db_provider = await self.repository.get_by_id(provider_id)
        if not db_provider:
            return None
        
        config = self._db_to_config(db_provider)
        is_available, _ = await self.discovery.test_provider(config)
        
        return LLMProviderResponse.from_config(config, is_available=is_available)
    
    async def list_providers(self, active_only: bool = False) -> List[LLMProviderResponse]:
        """List all providers"""
        db_providers = await self.repository.get_all(active_only=active_only)
        
        responses = []
        for db_provider in db_providers:
            config = self._db_to_config(db_provider)
            is_available, _ = await self.discovery.test_provider(config)
            responses.append(
                LLMProviderResponse.from_config(config, is_available=is_available)
            )
        
        return responses
    
    async def update_provider(
        self,
        provider_id: str,
        updates: LLMProviderUpdate
    ) -> Optional[LLMProviderResponse]:
        """Update provider"""
        db_provider = await self.repository.update(provider_id, updates)
        if not db_provider:
            return None
        
        # Update in registry
        config = self._db_to_config(db_provider)
        self.registry.register_provider(config)
        
        is_available, _ = await self.discovery.test_provider(config)
        
        logger.info(f"Updated provider: {db_provider.name}")
        
        return LLMProviderResponse.from_config(config, is_available=is_available)
    
    async def delete_provider(self, provider_id: str) -> bool:
        """Delete provider"""
        success = await self.repository.delete(provider_id)
        
        if success:
            # Remove from registry
            self.registry.unregister_provider(provider_id)
            logger.info(f"Deleted provider: {provider_id}")
        
        return success
    
    async def set_default_provider(self, provider_id: str) -> bool:
        """Set default provider"""
        success = await self.repository.set_default(provider_id)
        
        if success:
            # Update registry
            self.registry.set_default_provider(provider_id)
            logger.info(f"Set default provider: {provider_id}")
        
        return success
    
    async def test_provider(self, request: LLMProviderTestRequest) -> LLMProviderTestResponse:
        """Test provider connection"""
        import time
        
        # Get provider config
        if request.provider_id:
            db_provider = await self.repository.get_by_id(request.provider_id)
            if not db_provider:
                return LLMProviderTestResponse(
                    success=False,
                    provider_name="Unknown",
                    provider_type="unknown",
                    error_message=f"Provider {request.provider_id} not found"
                )
            config = self._db_to_config(db_provider)
        elif request.provider_config:
            config = LLMProviderConfig(**request.provider_config.dict())
        else:
            return LLMProviderTestResponse(
                success=False,
                provider_name="Unknown",
                provider_type="unknown",
                error_message="No provider specified"
            )
        
        # Test connection with a simple message
        try:
            start_time = time.time()
            
            # Create model instance
            model = create_chat_model(
                provider_config=config,
                temperature=0.0,
                max_tokens=50
            )
            
            # Send test message
            response = await model.ainvoke(request.test_message)
            
            latency = (time.time() - start_time) * 1000  # Convert to ms
            
            return LLMProviderTestResponse(
                success=True,
                provider_name=config.name,
                provider_type=config.provider_type,
                response_text=response.content,
                latency_ms=round(latency, 2)
            )
        
        except Exception as e:
            logger.error(f"Provider test failed for {config.name}: {e}")
            return LLMProviderTestResponse(
                success=False,
                provider_name=config.name,
                provider_type=config.provider_type,
                error_message=str(e)
            )
    
    async def discover_providers(self) -> List[LLMProviderConfig]:
        """Auto-discover available providers"""
        from app.core.llm.discovery import auto_discover_providers
        return await auto_discover_providers()
    
    async def sync_from_registry(self):
        """Sync database providers to runtime registry"""
        db_providers = await self.repository.get_all(active_only=True)
        
        for db_provider in db_providers:
            config = self._db_to_config(db_provider)
            self.registry.register_provider(config)
        
        logger.info(f"Synced {len(db_providers)} providers from database to registry")
