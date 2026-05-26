"""
LLM Provider Configuration Schemas

This module defines the data models for managing multiple LLM providers
with support for OpenAI, Anthropic, Ollama, Gemini, AWS Bedrock, and custom endpoints.
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, validator


class LLMProviderType(str, Enum):
    """Supported LLM provider types"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    GEMINI = "gemini"
    BEDROCK = "bedrock"
    CUSTOM = "custom"  # For any OpenAI-compatible API
    DISHCHAT = "dishchat"  # Internal Dish-Chat API


class LLMModelConfig(BaseModel):
    """Configuration for a specific model within a provider"""
    model_id: str = Field(..., description="Model identifier (e.g., 'gpt-4', 'claude-3-opus')")
    display_name: str = Field(..., description="Human-readable name for UI display")
    context_length: int = Field(default=4096, description="Maximum context window size")
    supports_streaming: bool = Field(default=True, description="Whether model supports streaming")
    supports_vision: bool = Field(default=False, description="Whether model supports image inputs")
    cost_per_1k_tokens: Optional[float] = Field(None, description="Approximate cost per 1K tokens (USD)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "model_id": "gpt-4o",
                "display_name": "GPT-4 Optimized",
                "context_length": 128000,
                "supports_streaming": True,
                "supports_vision": True,
                "cost_per_1k_tokens": 0.0050
            }
        }


class LLMProviderConfig(BaseModel):
    """Complete configuration for an LLM provider"""
    id: Optional[str] = Field(None, description="Unique identifier (generated if not provided)")
    name: str = Field(..., description="Display name for the provider")
    provider_type: LLMProviderType = Field(..., description="Type of provider")
    
    # API Configuration
    api_key: Optional[str] = Field(None, description="API key (encrypted in storage)")
    api_base: Optional[str] = Field(None, description="Base URL for API endpoint")
    
    # Models available from this provider
    models: List[LLMModelConfig] = Field(default_factory=list, description="Available models")
    
    # Provider settings
    is_active: bool = Field(default=True, description="Whether provider is enabled")
    is_default: bool = Field(default=False, description="Whether this is the default provider")
    
    # Additional configuration (provider-specific)
    extra_config: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific settings")
    
    # Metadata
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    @validator('api_base')
    def validate_api_base(cls, v, values):
        """Validate API base URL if provided"""
        if v:
            # Ensure it doesn't end with a slash
            return v.rstrip('/')
        return v
    
    @validator('models', always=True)
    def set_default_models(cls, v, values):
        """Set default models based on provider type if not specified"""
        if not v and 'provider_type' in values:
            provider_type = values['provider_type']
            
            if provider_type == LLMProviderType.OPENAI:
                return [
                    LLMModelConfig(
                        model_id="gpt-4o",
                        display_name="GPT-4 Optimized",
                        context_length=128000,
                        supports_vision=True
                    ),
                    LLMModelConfig(
                        model_id="gpt-4o-mini",
                        display_name="GPT-4 Mini",
                        context_length=128000
                    ),
                    LLMModelConfig(
                        model_id="gpt-3.5-turbo",
                        display_name="GPT-3.5 Turbo",
                        context_length=16385
                    )
                ]
            elif provider_type == LLMProviderType.ANTHROPIC:
                return [
                    LLMModelConfig(
                        model_id="claude-3-5-sonnet-20241022",
                        display_name="Claude 3.5 Sonnet",
                        context_length=200000,
                        supports_vision=True
                    ),
                    LLMModelConfig(
                        model_id="claude-3-5-haiku-20241022",
                        display_name="Claude 3.5 Haiku",
                        context_length=200000
                    )
                ]
            elif provider_type == LLMProviderType.GEMINI:
                return [
                    LLMModelConfig(
                        model_id="gemini-1.5-pro",
                        display_name="Gemini 1.5 Pro",
                        context_length=1000000,
                        supports_vision=True
                    ),
                    LLMModelConfig(
                        model_id="gemini-1.5-flash",
                        display_name="Gemini 1.5 Flash",
                        context_length=1000000
                    )
                ]
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "OpenAI GPT",
                "provider_type": "openai",
                "api_key": "sk-proj-...",
                "models": [
                    {
                        "model_id": "gpt-4o",
                        "display_name": "GPT-4 Optimized",
                        "context_length": 128000
                    }
                ],
                "is_active": True,
                "is_default": True
            }
        }


class LLMProviderCreate(BaseModel):
    """Schema for creating a new LLM provider"""
    name: str
    provider_type: LLMProviderType
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    models: List[LLMModelConfig] = Field(default_factory=list)
    is_active: bool = True
    is_default: bool = False
    extra_config: Dict[str, Any] = Field(default_factory=dict)


class LLMProviderUpdate(BaseModel):
    """Schema for updating an existing LLM provider"""
    name: Optional[str] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    models: Optional[List[LLMModelConfig]] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    extra_config: Optional[Dict[str, Any]] = None


class LLMProviderResponse(BaseModel):
    """Schema for LLM provider API responses (masks API key)"""
    id: str
    name: str
    provider_type: LLMProviderType
    api_key_set: bool = Field(..., description="Whether API key is configured (actual key is masked)")
    api_base: Optional[str] = None
    models: List[LLMModelConfig]
    is_active: bool
    is_default: bool
    is_available: bool = Field(..., description="Whether provider is currently reachable")
    created_at: str
    updated_at: str
    
    @classmethod
    def from_config(cls, config: LLMProviderConfig, is_available: bool = True):
        """Convert LLMProviderConfig to response (masking sensitive data)"""
        return cls(
            id=config.id or "unknown",
            name=config.name,
            provider_type=config.provider_type,
            api_key_set=bool(config.api_key),
            api_base=config.api_base,
            models=config.models,
            is_active=config.is_active,
            is_default=config.is_default,
            is_available=is_available,
            created_at=config.created_at or "",
            updated_at=config.updated_at or ""
        )


class LLMProviderTestRequest(BaseModel):
    """Schema for testing an LLM provider connection"""
    provider_id: Optional[str] = None
    provider_config: Optional[LLMProviderCreate] = None
    test_message: str = Field(default="Hello, this is a test message. Please respond with 'OK'.")


class LLMProviderTestResponse(BaseModel):
    """Schema for LLM provider test results"""
    success: bool
    provider_name: str
    provider_type: LLMProviderType
    response_text: Optional[str] = None
    error_message: Optional[str] = None
    latency_ms: Optional[float] = None


class DiscoveredProvider(BaseModel):
    """Schema for auto-discovered LLM providers"""
    name: str
    provider_type: LLMProviderType
    api_base: Optional[str] = None
    detected_models: List[str] = Field(default_factory=list)
    is_local: bool = Field(default=False, description="Whether provider is running locally")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence (0-1)")
    source: str = Field(..., description="How provider was discovered (e.g., 'env_var', 'network_scan')")
