"""
Repository for LLM provider database operations
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError

from app.llm_config.models import LLMProviderModel
from app.core.llm.schemas import LLMProviderConfig, LLMProviderCreate, LLMProviderUpdate


class LLMProviderRepository:
    """Database operations for LLM providers"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, provider: LLMProviderCreate) -> LLMProviderModel:
        """Create a new provider"""
        # Generate ID if not provided
        provider_id = provider.name.lower().replace(" ", "_")
        
        db_provider = LLMProviderModel(
            id=provider_id,
            name=provider.name,
            provider_type=provider.provider_type.value,
            api_key=provider.api_key,
            api_base=provider.api_base,
            models=[m.dict() for m in provider.models],
            extra_config=provider.extra_config,
            is_active=provider.is_active,
            is_default=provider.is_default
        )
        
        self.session.add(db_provider)
        
        try:
            await self.session.commit()
            await self.session.refresh(db_provider)
            return db_provider
        except IntegrityError:
            await self.session.rollback()
            raise ValueError(f"Provider with ID '{provider_id}' already exists")
    
    async def get_by_id(self, provider_id: str) -> Optional[LLMProviderModel]:
        """Get provider by ID"""
        result = await self.session.execute(
            select(LLMProviderModel).where(LLMProviderModel.id == provider_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, active_only: bool = False) -> List[LLMProviderModel]:
        """Get all providers"""
        query = select(LLMProviderModel)
        
        if active_only:
            query = query.where(LLMProviderModel.is_active == True)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_default(self) -> Optional[LLMProviderModel]:
        """Get the default provider"""
        result = await self.session.execute(
            select(LLMProviderModel)
            .where(LLMProviderModel.is_default == True)
            .where(LLMProviderModel.is_active == True)
        )
        return result.scalar_one_or_none()
    
    async def update(
        self,
        provider_id: str,
        updates: LLMProviderUpdate
    ) -> Optional[LLMProviderModel]:
        """Update a provider"""
        db_provider = await self.get_by_id(provider_id)
        if not db_provider:
            return None
        
        # Apply updates
        update_data = updates.dict(exclude_unset=True)
        
        # Handle models separately (convert to dict)
        if "models" in update_data and update_data["models"]:
            update_data["models"] = [m.dict() for m in update_data["models"]]
        
        for key, value in update_data.items():
            setattr(db_provider, key, value)
        
        await self.session.commit()
        await self.session.refresh(db_provider)
        return db_provider
    
    async def delete(self, provider_id: str) -> bool:
        """Delete a provider"""
        result = await self.session.execute(
            delete(LLMProviderModel).where(LLMProviderModel.id == provider_id)
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def set_default(self, provider_id: str) -> bool:
        """Set a provider as the default (unsets others)"""
        # First, unset all defaults
        await self.session.execute(
            update(LLMProviderModel).values(is_default=False)
        )
        
        # Then set the new default
        result = await self.session.execute(
            update(LLMProviderModel)
            .where(LLMProviderModel.id == provider_id)
            .values(is_default=True)
        )
        
        await self.session.commit()
        return result.rowcount > 0
