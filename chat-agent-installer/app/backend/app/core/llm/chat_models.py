"""
Multi-Provider LLM Chat Models Factory

Supports:
- OpenAI (ChatGPT)
- Anthropic (Claude)
- Google Gemini
- Ollama (local)
- AWS Bedrock  
- Custom OpenAI-compatible endpoints
"""
from functools import cache, lru_cache
from typing import Optional, Dict
import logging

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_aws import ChatBedrockConverse

# Import provider-specific implementations
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

try:
    from langchain_ollama import ChatOllama
except ImportError:
    ChatOllama = None

from app.config import get_settings
from app.core.llm.schemas import LLMProviderType, LLMProviderConfig, LLMModelConfig

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMProviderRegistry:
    """
    Registry for managing multiple LLM providers at runtime.
    Allows adding/removing providers without restarting the application.
    """
    
    def __init__(self):
        self._providers: Dict[str, LLMProviderConfig] = {}
        self._default_provider_id: Optional[str] = None
        self._initialize_from_env()
    
    def _initialize_from_env(self):
        """Initialize providers from environment variables for backward compatibility"""
        # Check if PLLM_PROVIDER is configured in env
        if hasattr(settings, 'PLLM_PROVIDER') and settings.PLLM_PROVIDER:
            provider_type = settings.PLLM_PROVIDER
            
            # Create default provider from env vars
            if provider_type == "openai":
                api_key = getattr(settings, 'OPENAI_API_KEY', None)
                api_base = getattr(settings, 'PLLM_API_BASE', None)
                model_id = getattr(settings, 'PLLM_MODEL', 'gpt-4o')
                if api_key:
                    # If using Ollama or custom endpoint, use the specified model
                    # Otherwise use default OpenAI models
                    if api_base and 'ollama' in api_base.lower():
                        # Ollama: use the specified model from env
                        models = [
                            LLMModelConfig(
                                model_id=model_id,
                                display_name=f"Ollama: {model_id}",
                                context_length=200000,
                                supports_streaming=True
                            )
                        ]
                    else:
                        # OpenAI: allow model override from env
                        models = None  # Will use defaults, but can be overridden
                        if model_id != 'gpt-4o':
                            # User specified a non-default model, use it
                            models = [
                                LLMModelConfig(
                                    model_id=model_id,
                                    display_name=model_id,
                                    context_length=128000,
                                    supports_streaming=True
                                )
                            ]
                    
                    config = LLMProviderConfig(
                        id="env_openai",
                        name="OpenAI (from env)",
                        provider_type=LLMProviderType.OPENAI,
                        api_key=api_key,
                        api_base=api_base,
                        models=models or [],  # Let validator set defaults if empty
                        is_default=True,
                        is_active=True
                    )
                    self.register_provider(config)
            
            elif provider_type == "anthropic":
                api_key = getattr(settings, 'ANTHROPIC_API_KEY', None)
                api_base = getattr(settings, 'PLLM_API_BASE', None)
                if api_key:
                    config = LLMProviderConfig(
                        id="env_anthropic",
                        name="Anthropic (from env)",
                        provider_type=LLMProviderType.ANTHROPIC,
                        api_key=api_key,
                        api_base=api_base,
                        is_default=True,
                        is_active=True
                    )
                    self.register_provider(config)
            
            elif provider_type == "aws-bedrock":
                config = LLMProviderConfig(
                    id="env_bedrock",
                    name="AWS Bedrock (from env)",
                    provider_type=LLMProviderType.BEDROCK,
                    is_default=True,
                    is_active=True
                )
                self.register_provider(config)
    
    def register_provider(self, config: LLMProviderConfig):
        """Register a new provider"""
        if not config.id:
            # Generate ID from name
            config.id = config.name.lower().replace(" ", "_")
        
        self._providers[config.id] = config
        
        if config.is_default or not self._default_provider_id:
            self._default_provider_id = config.id
        
        logger.info(f"Registered LLM provider: {config.name} ({config.provider_type})")
    
    def unregister_provider(self, provider_id: str):
        """Remove a provider from registry"""
        if provider_id in self._providers:
            del self._providers[provider_id]
            if self._default_provider_id == provider_id:
                # Set new default
                self._default_provider_id = next(iter(self._providers.keys()), None)
    
    def get_provider(self, provider_id: Optional[str] = None) -> Optional[LLMProviderConfig]:
        """Get provider configuration by ID, or default if None"""
        if provider_id:
            return self._providers.get(provider_id)
        return self._providers.get(self._default_provider_id) if self._default_provider_id else None
    
    def list_providers(self, active_only: bool = True) -> Dict[str, LLMProviderConfig]:
        """List all registered providers"""
        if active_only:
            return {k: v for k, v in self._providers.items() if v.is_active}
        return self._providers.copy()
    
    def set_default_provider(self, provider_id: str):
        """Set the default provider"""
        if provider_id in self._providers:
            # Unset previous default
            if self._default_provider_id:
                self._providers[self._default_provider_id].is_default = False
            # Set new default
            self._providers[provider_id].is_default = True
            self._default_provider_id = provider_id


# Global provider registry
_provider_registry = LLMProviderRegistry()


def get_provider_registry() -> LLMProviderRegistry:
    """Get the global provider registry"""
    return _provider_registry


def create_chat_model(
    provider_config: LLMProviderConfig,
    model_id: Optional[str] = None,
    temperature: float = 0.6,
    max_tokens: int = 4096,
    **kwargs
) -> BaseChatModel:
    """
    Create a chat model instance from provider configuration.
    
    Args:
        provider_config: LLM provider configuration
        model_id: Specific model ID to use (uses first model if not specified)
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        **kwargs: Additional provider-specific arguments
    
    Returns:
        BaseChatModel instance
    
    Raises:
        NotImplementedError: If provider type is not supported
        ImportError: If required library is not installed
    """
    provider_type = provider_config.provider_type
    
    # Determine which model to use
    if not model_id and provider_config.models:
        model_id = provider_config.models[0].model_id
    
    # OpenAI
    if provider_type == LLMProviderType.OPENAI:
        if ChatOpenAI is None:
            raise ImportError("langchain-openai is not installed. Install with: pip install langchain-openai")
        
        return ChatOpenAI(
            model=model_id or "gpt-4o",
            api_key=provider_config.api_key,
            base_url=provider_config.api_base,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    # Anthropic
    elif provider_type == LLMProviderType.ANTHROPIC:
        if ChatAnthropic is None:
            raise ImportError("langchain-anthropic is not installed. Install with: pip install langchain-anthropic")
        
        return ChatAnthropic(
            model=model_id or "claude-3-5-sonnet-20241022",
            api_key=provider_config.api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    # Google Gemini
    elif provider_type == LLMProviderType.GEMINI:
        if ChatGoogleGenerativeAI is None:
            raise ImportError("langchain-google-genai is not installed. Install with: pip install langchain-google-genai")
        
        return ChatGoogleGenerativeAI(
            model=model_id or "gemini-1.5-pro",
            google_api_key=provider_config.api_key,
            temperature=temperature,
            max_output_tokens=max_tokens,
            **kwargs
        )
    
    # Ollama (local)
    elif provider_type == LLMProviderType.OLLAMA:
        if ChatOllama is None:
            raise ImportError("langchain-ollama is not installed. Install with: pip install langchain-ollama")
        
        return ChatOllama(
            model=model_id or "llama3",
            base_url=provider_config.api_base or "http://localhost:11434",
            temperature=temperature,
            num_predict=max_tokens,
            **kwargs
        )
    
    # AWS Bedrock
    elif provider_type == LLMProviderType.BEDROCK:
        return ChatBedrockConverse(
            model=model_id or settings.PLLM_MODEL,
            max_tokens=max_tokens,
            region_name=settings.AWS_REGION,
            disable_streaming=False,
            **kwargs
        )
    
    # Custom / OpenAI-compatible
    elif provider_type == LLMProviderType.CUSTOM:
        if ChatOpenAI is None:
            raise ImportError("langchain-openai is not installed. Install with: pip install langchain-openai")
        
        if not provider_config.api_base:
            raise ValueError("Custom provider requires api_base URL")
        
        return ChatOpenAI(
            model=model_id or "default",
            api_key=provider_config.api_key or "not-needed",
            base_url=provider_config.api_base,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    else:
        raise NotImplementedError(f"Provider type {provider_type} is not yet implemented")


def get_model(
    efficient: bool = False,
    provider_id: Optional[str] = None,
    model_id: Optional[str] = None
) -> BaseChatModel:
    """
    Get a chat model instance (backward compatible interface).
    
    Args:
        efficient: If True, use smaller/cheaper model
        provider_id: Specific provider to use (uses default if None)
        model_id: Specific model to use
    
    Returns:
        BaseChatModel instance
    """
    registry = get_provider_registry()
    provider_config = registry.get_provider(provider_id)
    
    if not provider_config:
        # Fallback to legacy bedrock for backward compatibility
        logger.warning("No LLM providers configured, falling back to AWS Bedrock")
        provider_config = LLMProviderConfig(
            id="fallback_bedrock",
            name="AWS Bedrock (Fallback)",
            provider_type=LLMProviderType.BEDROCK,
            is_active=True
        )
    
    # Select model based on efficient flag
    if efficient and len(provider_config.models) > 1:
        # Use second model (typically cheaper/faster)
        model_id = model_id or provider_config.models[1].model_id
    elif not model_id and provider_config.models:
        # Use first model (typically most capable)
        model_id = provider_config.models[0].model_id
    
    return create_chat_model(
        provider_config=provider_config,
        model_id=model_id,
        temperature=settings.DEFAULT_TEMP,
        max_tokens=settings.MAX_OUTPUT_COUNT
    )
