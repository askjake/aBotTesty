from functools import cache

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import ConfigurableField
from langchain_aws import ChatBedrockConverse

from app.config import get_settings

settings = get_settings()

@cache
def get_model(efficient: bool = False) -> BaseChatModel:
    """
    Get chat model objects.
    Args:
        efficient: use smaller and more cost friendly model

    Returns:
        A Langchain chat model object.
    """
    if efficient and settings.ELLM_MODEL:
        if settings.ELLM_PROVIDER == "aws-bedrock":
            model = ChatBedrockConverse(
                model=settings.ELLM_MODEL,
                max_tokens=4096,
                region_name=settings.AWS_REGION,
                disable_streaming=False
            )
        else:
            raise NotImplementedError(f"Provider {settings.ELLM_PROVIDER} not implemented yet")
    else:
        if settings.PLLM_PROVIDER == "aws-bedrock":
            model = ChatBedrockConverse(
                model=settings.PLLM_MODEL,
                max_tokens=settings.MAX_OUTPUT_COUNT,
                region_name=settings.AWS_REGION,
                disable_streaming=False
            )
        else:
            raise NotImplementedError(f"Provider {settings.PLLM_PROVIDER} not implemented yet")

    return model