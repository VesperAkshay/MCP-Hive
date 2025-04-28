"""Factory for creating LLM provider instances."""

import os
import logging
from typing import Dict, Optional

from .gemini_provider import GeminiProvider
from .groq_provider import GroqProvider

logger = logging.getLogger(__name__)

async def create_provider(provider_name: str, api_key: Optional[str] = None) -> Dict:
    """
    Create an LLM provider instance based on name.
    
    Args:
        provider_name: The name of the provider (gemini, groq)
        api_key: Optional API key override (if None, will use environment variables)
        
    Returns:
        Provider instance
    
    Raises:
        ValueError: If the provider name is unknown or API key not available
    """
    if provider_name.lower() == "gemini":
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        provider = GeminiProvider(key)
        await provider.initialize()
        return provider
        
    elif provider_name.lower() == "groq":
        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        provider = GroqProvider(key)
        await provider.initialize()
        return provider
        
    else:
        raise ValueError(f"Unknown provider: {provider_name}")


async def create_all_available_providers() -> Dict[str, object]:
    """
    Create instances of all available LLM providers based on environment variables.
    
    Returns:
        Dictionary mapping provider names to provider instances
    """
    providers = {}
    
    # Try to create Gemini provider
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if gemini_api_key:
        try:
            providers["gemini"] = await create_provider("gemini", gemini_api_key)
            logger.info("Initialized Gemini provider")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini provider: {e}")
    
    # Try to create Groq provider
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key:
        try:
            providers["groq"] = await create_provider("groq", groq_api_key)
            logger.info("Initialized Groq provider")
        except Exception as e:
            logger.error(f"Failed to initialize Groq provider: {e}")
    
    return providers 