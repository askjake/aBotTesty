"""
FastAPI router for LLM provider management endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db_session
from app.llm_config.repository import LLMProviderRepository
from app.llm_config.service import LLMProviderService
from app.core.llm.schemas import (
    LLMProviderCreate,
    LLMProviderUpdate,
    LLMProviderResponse,
    LLMProviderTestRequest,
    LLMProviderTestResponse,
    LLMProviderConfig
)

router = APIRouter(prefix="/llm-providers", tags=["LLM Providers"])


def get_llm_service(session: AsyncSession = Depends(get_db_session)) -> LLMProviderService:
    """Dependency to get LLM provider service"""
    repository = LLMProviderRepository(session)
    return LLMProviderService(repository)


@router.post("/", response_model=LLMProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    provider: LLMProviderCreate,
    service: LLMProviderService = Depends(get_llm_service)
):
    """
    Create a new LLM provider configuration.
    
    Example:
    ```json
    {
        "name": "My OpenAI",
        "provider_type": "openai",
        "api_key": "sk-proj-...",
        "is_default": true
    }
    ```
    """
    try:
        return await service.create_provider(provider)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=List[LLMProviderResponse])
async def list_providers(
    active_only: bool = False,
    service: LLMProviderService = Depends(get_llm_service)
):
    """
    List all configured LLM providers.
    
    Query Parameters:
    - active_only: If true, only return active providers
    """
    return await service.list_providers(active_only=active_only)


@router.get("/{provider_id}", response_model=LLMProviderResponse)
async def get_provider(
    provider_id: str,
    service: LLMProviderService = Depends(get_llm_service)
):
    """Get a specific provider by ID"""
    provider = await service.get_provider(provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_id}' not found"
        )
    return provider


@router.patch("/{provider_id}", response_model=LLMProviderResponse)
async def update_provider(
    provider_id: str,
    updates: LLMProviderUpdate,
    service: LLMProviderService = Depends(get_llm_service)
):
    """Update an existing provider"""
    provider = await service.update_provider(provider_id, updates)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_id}' not found"
        )
    return provider


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: str,
    service: LLMProviderService = Depends(get_llm_service)
):
    """Delete a provider"""
    success = await service.delete_provider(provider_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_id}' not found"
        )
    return None


@router.post("/{provider_id}/set-default", response_model=dict)
async def set_default_provider(
    provider_id: str,
    service: LLMProviderService = Depends(get_llm_service)
):
    """Set a provider as the default"""
    success = await service.set_default_provider(provider_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_id}' not found"
        )
    return {"message": f"Provider '{provider_id}' set as default"}


@router.post("/test", response_model=LLMProviderTestResponse)
async def test_provider(
    request: LLMProviderTestRequest,
    service: LLMProviderService = Depends(get_llm_service)
):
    """
    Test a provider connection.
    
    You can test:
    - An existing provider by ID
    - A new configuration before saving
    
    Example:
    ```json
    {
        "provider_id": "my_openai",
        "test_message": "Say hello!"
    }
    ```
    
    Or test a configuration before creating:
    ```json
    {
        "provider_config": {
            "name": "Test Provider",
            "provider_type": "openai",
            "api_key": "sk-..."
        }
    }
    ```
    """
    return await service.test_provider(request)


@router.post("/discover", response_model=List[LLMProviderConfig])
async def discover_providers(
    service: LLMProviderService = Depends(get_llm_service)
):
    """
    Auto-discover available LLM providers.
    
    This will scan for:
    - API keys in environment variables
    - Local Ollama instances
    - Other local LLM services
    
    Returns discovered providers that can be added with a single click.
    """
    return await service.discover_providers()
