"""
LLM Provider Auto-Discovery

Automatically detects available LLM providers from:
- Environment variables (API keys)
- Local network (Ollama, local APIs)
- System configuration
"""
import os
import logging
import asyncio
from typing import List, Optional
import httpx

from app.core.llm.schemas import (
    LLMProviderType,
    LLMProviderConfig,
    LLMModelConfig,
    DiscoveredProvider
)

logger = logging.getLogger(__name__)


class ProviderDiscovery:
    """Auto-discovery service for LLM providers"""
    
    # Environment variable mappings
    ENV_VAR_MAP = {
        LLMProviderType.OPENAI: "OPENAI_API_KEY",
        LLMProviderType.ANTHROPIC: "ANTHROPIC_API_KEY",
        LLMProviderType.GEMINI: "GOOGLE_API_KEY",
    }
    
    # Known Ollama endpoints to check
    OLLAMA_ENDPOINTS = [
        "http://localhost:11434",
        "http://127.0.0.1:11434",
        "http://ollama:11434",  # Docker compose
    ]
    
    async def discover_all(self) -> List[DiscoveredProvider]:
        """Run all discovery methods and return found providers"""
        discovered = []
        
        # Discover from environment variables
        env_providers = await self.discover_from_env()
        discovered.extend(env_providers)
        
        # Discover local Ollama instances
        ollama_providers = await self.discover_ollama()
        discovered.extend(ollama_providers)
        
        # Log results
        logger.info(f"Auto-discovery found {len(discovered)} providers")
        for provider in discovered:
            logger.info(f"  - {provider.name} ({provider.provider_type}) from {provider.source}")
        
        return discovered
    
    async def discover_from_env(self) -> List[DiscoveredProvider]:
        """Discover providers from environment variables"""
        discovered = []
        
        for provider_type, env_var in self.ENV_VAR_MAP.items():
            api_key = os.getenv(env_var)
            
            if api_key:
                provider = DiscoveredProvider(
                    name=f"{provider_type.value.title()} (from {env_var})",
                    provider_type=provider_type,
                    confidence=1.0,
                    source=f"env_var:{env_var}",
                    is_local=False
                )
                discovered.append(provider)
                logger.debug(f"Found {env_var} in environment")
        
        return discovered
    
    async def discover_ollama(self) -> List[DiscoveredProvider]:
        """Discover local Ollama instances"""
        discovered = []
        
        for endpoint in self.OLLAMA_ENDPOINTS:
            try:
                # Try to connect to Ollama API
                async with httpx.AsyncClient(timeout=2.0) as client:
                    response = await client.get(f"{endpoint}/api/tags")
                    
                    if response.status_code == 200:
                        data = response.json()
                        models = [m["name"] for m in data.get("models", [])]
                        
                        provider = DiscoveredProvider(
                            name=f"Ollama ({endpoint})",
                            provider_type=LLMProviderType.OLLAMA,
                            api_base=endpoint,
                            detected_models=models,
                            is_local=True,
                            confidence=1.0,
                            source=f"network_scan:{endpoint}"
                        )
                        discovered.append(provider)
                        logger.info(f"Found Ollama at {endpoint} with {len(models)} models")
                        break  # Only need one Ollama instance
            
            except Exception as e:
                logger.debug(f"No Ollama found at {endpoint}: {e}")
                continue
        
        return discovered
    
    async def test_provider_connection(
        self,
        provider_config: LLMProviderConfig,
        test_message: str = "Hello"
    ) -> tuple[bool, Optional[str], Optional[float]]:
        """
        Test if a provider is reachable and working.
        
        Returns:
            (success, response_text, latency_ms)
        """
        import time
        from app.core.llm.chat_models import create_chat_model
        
        try:
            start_time = time.time()
            
            # Create model instance
            model = create_chat_model(
                provider_config=provider_config,
                temperature=0.0,
                max_tokens=50
            )
            
            # Try to invoke with a simple message
            response = await model.ainvoke(test_message)
            
            latency = (time.time() - start_time) * 1000  # Convert to ms
            
            return (True, response.content, latency)
        
        except Exception as e:
            logger.error(f"Provider test failed for {provider_config.name}: {e}")
            return (False, None, None)



# Additional helper functions for compatibility
def get_discovery_service() -> ProviderDiscovery:
    """Get the global discovery service instance (alias for get_discovery)"""
    return _discovery


async def auto_discover_providers() -> List[DiscoveredProvider]:
    """
    Auto-discover all available providers.
    Convenience function that calls discovery.discover_all()
    """
    return await _discovery.discover_all()

# Global discovery instance
_discovery = ProviderDiscovery()


def get_discovery() -> ProviderDiscovery:
    """Get the global discovery instance"""
    return _discovery
