"""Factory for creating LLM provider instances."""

import os
import logging
from typing import Dict, Optional

from .groq_provider import GroqProvider

logger = logging.getLogger(__name__)

async def create_provider(provider_name: str, api_key: Optional[str] = None) -> Dict:
    """
    Create an LLM provider instance based on name.
    
    Args:
        provider_name: The name of the provider (currently only groq is supported)
        api_key: Optional API key override (if None, will use environment variables)
        
    Returns:
        Provider instance
    
    Raises:
        ValueError: If the provider name is unknown or API key not available
    """
    # Automatically redirect all requests to Groq
    if provider_name.lower() == "gemini":
        logger.warning("Gemini provider is not supported in this build. Using Groq instead.")
        provider_name = "groq"
        
    if provider_name.lower() == "groq":
        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        provider = GroqProvider(key)
        await provider.initialize()
        return provider
        
    else:
        raise ValueError(f"Unknown provider: {provider_name}. Only Groq is supported in this build.")


async def create_all_available_providers() -> Dict[str, object]:
    """
    Create instances of all available LLM providers based on environment variables.
    
    Returns:
        Dictionary mapping provider names to provider instances
    """
    providers = {}
    
    # Skip trying to create Gemini provider
    
    # Try to create Groq provider
    groq_api_key = os.getenv("GROQ_API_KEY") or os.getenv("GOOGLE_API_KEY")  # Try to use Google API key as fallback
    if groq_api_key:
        try:
            providers["groq"] = await create_provider("groq", groq_api_key)
            # Also set as default provider
            providers["default"] = providers["groq"]
            logger.info("Initialized Groq provider")
        except Exception as e:
            logger.error(f"Failed to initialize Groq provider: {e}")
    
    return providers 