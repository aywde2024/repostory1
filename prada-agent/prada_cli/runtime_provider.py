"""
PRADA CLI Runtime Provider Resolution
Resolves (provider, model) → (api_mode, credentials, base_url)
Supports 18+ LLM providers
"""

import os
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


PROVIDER_FAMILIES = {
    # AI Aggregators
    "openrouter": {
        "api_modes": ["chat_completions", "codex_responses"],
        "auth": "bearer_token",
        "base_url": "https://openrouter.ai/api/v1",
        "env_var": "OPENROUTER_API_KEY",
        "aliases": ["or"],
    },
    "nous": {
        "api_modes": ["chat_completions"],
        "auth": "bearer_token",
        "base_url": "https://api.nousresearch.com/v1",
        "env_var": "NOUS_API_KEY",
        "aliases": ["nousresearch"],
    },
    
    # Native Providers
    "openai": {
        "api_modes": ["chat_completions", "codex_responses"],
        "auth": "bearer_token",
        "base_url": "https://api.openai.com/v1",
        "env_var": "OPENAI_API_KEY",
        "special": ["o1-series reasoning", "function calling v2"],
    },
    "anthropic": {
        "api_modes": ["anthropic_messages"],
        "auth": "x-api-key + bearer",
        "base_url": "https://api.anthropic.com/v1",
        "env_var": "ANTHROPIC_API_KEY",
        "special": ["prompt caching", "beta features"],
    },
    "gemini": {
        "api_modes": ["chat_completions"],
        "auth": "oauth2 or api_key",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "env_var": "GEMINI_API_KEY",
        "oauth_flow": True,
    },
    "xai": {
        "api_modes": ["codex_responses"],
        "auth": "bearer_token",
        "base_url": "https://api.x.ai/v1",
        "env_var": "XAI_API_KEY",
        "special": ["x-grok-conv-id header", "encrypted_content"],
        "aliases": ["grok"],
    },
    
    # Chinese Providers
    "moonshot": {
        "api_modes": ["chat_completions"],
        "auth": "bearer_token",
        "base_url": "https://api.moonshot.cn/v1",
        "env_var": "MOONSHOT_API_KEY",
        "aliases": ["kimi"],
    },
    "minimax": {
        "api_modes": ["chat_completions"],
        "auth": "bearer_token",
        "base_url": "https://api.minimax.chat/v1",
        "env_var": "MINIMAX_API_KEY",
    },
    "zhipu": {
        "api_modes": ["chat_completions"],
        "auth": "bearer_token",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "env_var": "ZHIPU_API_KEY",
        "aliases": ["glm", "z.ai"],
    },
    
    # Self-hosted / Open Source
    "ollama": {
        "api_modes": ["chat_completions"],
        "auth": "none",
        "base_url": "http://localhost:11434/v1",
        "env_var": None,
        "configurable": ["base_url"],
    },
    "vllm": {
        "api_modes": ["chat_completions"],
        "auth": "bearer_token?",
        "base_url": "http://localhost:8000/v1",
        "env_var": "VLLM_API_KEY?",
        "configurable": ["base_url"],
    },
    "lmstudio": {
        "api_modes": ["chat_completions"],
        "auth": "none",
        "base_url": "http://localhost:1234/v1",
        "env_var": None,
    },
    
    # Other Aggregators
    "together": {
        "api_modes": ["chat_completions"],
        "auth": "bearer_token",
        "base_url": "https://api.together.xyz/v1",
        "env_var": "TOGETHER_API_KEY",
    },
    "fireworks": {
        "api_modes": ["chat_completions"],
        "auth": "bearer_token",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "env_var": "FIREWORKS_API_KEY",
    },
    "groq": {
        "api_modes": ["chat_completions"],
        "auth": "bearer_token",
        "base_url": "https://api.groq.com/openai/v1",
        "env_var": "GROQ_API_KEY",
    },
    "deepseek": {
        "api_modes": ["chat_completions"],
        "auth": "bearer_token",
        "base_url": "https://api.deepseek.com/v1",
        "env_var": "DEEPSEEK_API_KEY",
    },
    "mistral": {
        "api_modes": ["chat_completions"],
        "auth": "bearer_token",
        "base_url": "https://api.mistral.ai/v1",
        "env_var": "MISTRAL_API_KEY",
    },
    "cohere": {
        "api_modes": ["chat_completions"],
        "auth": "bearer_token",
        "base_url": "https://api.cohere.com/v1",
        "env_var": "COHERE_API_KEY",
    },
    
    # Custom Endpoint
    "custom": {
        "api_modes": ["chat_completions", "anthropic_messages", "codex_responses"],
        "auth": "configurable",
        "base_url": "configurable",
        "env_var": "CUSTOM_API_KEY?",
        "requires": ["base_url", "api_mode"],
    },
}


def resolve_runtime_provider(provider: str, model: str) -> Dict[str, Any]:
    """
    Resolve (provider, model) to runtime configuration.
    
    Returns dict with:
    - api_mode: chat_completions | anthropic_messages | codex_responses
    - credentials: dict with api_key and other auth info
    - base_url: API endpoint URL
    - provider: normalized provider name
    - model: model identifier
    """
    # Normalize provider (handle aliases)
    original_provider = provider
    provider = provider.lower()
    provider_info = _get_provider_info(provider)
    
    if not provider_info:
        raise ValueError(f"Unknown provider: {provider}")
    
    # Get the canonical provider name (resolve aliases)
    canonical_provider = provider
    if original_provider.lower() not in PROVIDER_FAMILIES:
        # Find canonical name for alias
        for prov_name, prov_info in PROVIDER_FAMILIES.items():
            aliases = prov_info.get('aliases', [])
            if provider in aliases:
                canonical_provider = prov_name
                break
    
    # Determine API mode
    api_mode = _determine_api_mode(
        provider=canonical_provider,
        base_url=provider_info.get('base_url', ''),
        model=model,
        available_modes=provider_info.get('api_modes', ['chat_completions']),
    )
    
    # Get credentials
    credentials = _get_credentials(provider_info, canonical_provider)
    
    # Handle custom provider
    if canonical_provider == "custom":
        base_url = os.environ.get("CUSTOM_BASE_URL")
        if not base_url:
            raise ValueError("CUSTOM_BASE_URL environment variable required for custom provider")
        
        # For custom provider, also allow custom API mode
        custom_api_mode = os.environ.get("CUSTOM_API_MODE", "chat_completions")
        if custom_api_mode not in ["chat_completions", "anthropic_messages", "codex_responses"]:
            logger.warning(f"Unknown CUSTOM_API_MODE '{custom_api_mode}', defaulting to chat_completions")
            custom_api_mode = "chat_completions"
        api_mode = custom_api_mode
    else:
        base_url = provider_info.get('base_url')
    
    return {
        "api_mode": api_mode,
        "credentials": credentials,
        "base_url": base_url,
        "provider": canonical_provider,
        "model": model,
        "provider_info": provider_info,
    }


def _get_provider_info(provider: str) -> Optional[Dict]:
    """Get provider info by name or alias"""
    # Direct match
    if provider in PROVIDER_FAMILIES:
        return PROVIDER_FAMILIES[provider]
    
    # Check aliases
    for prov_name, prov_info in PROVIDER_FAMILIES.items():
        aliases = prov_info.get('aliases', [])
        if provider in aliases:
            return prov_info
    
    return None


def _determine_api_mode(
    provider: str,
    base_url: str,
    model: str,
    available_modes: list,
) -> str:
    """Determine which API mode to use"""
    # Anthropic always uses anthropic_messages
    if provider == "anthropic" or "anthropic.com" in base_url:
        return "anthropic_messages"
    
    # xAI/Grok uses codex_responses
    if provider == "xai" or "x.ai" in base_url or "grok" in model.lower():
        return "codex_responses"
    
    # OpenAI Codex models use codex_responses
    if "openai.com" in base_url and "codex" in model.lower():
        return "codex_responses"
    
    # Default to chat_completions
    return "chat_completions"


def _get_credentials(provider_info: Dict, provider: str = None) -> Dict[str, Optional[str]]:
    """Get credentials for provider from environment"""
    env_var = provider_info.get('env_var')
    
    credentials = {
        'api_key': None,
        'auth_type': provider_info.get('auth', 'bearer_token'),
    }
    
    if env_var and env_var != "none":
        # Handle optional env var (ending with ?)
        if env_var.endswith('?'):
            env_var = env_var.rstrip('?')
            credentials['api_key'] = os.environ.get(env_var)
        else:
            credentials['api_key'] = os.environ.get(env_var)
    
    # Check if required credential is missing
    if credentials['api_key'] is None and not provider_info.get('oauth_flow'):
        if env_var and not env_var.endswith('?'):
            # For non-custom providers, log warning about missing credentials
            if provider != "custom":
                logger.warning(f"Missing required environment variable: {env_var}")
                logger.warning(f"Please set {env_var} in your .env file or environment")
    
    # Special handling for OAuth providers
    if provider_info.get('oauth_flow'):
        credentials['oauth_enabled'] = True
    
    return credentials


def get_available_providers() -> list:
    """Get list of available provider names"""
    return list(PROVIDER_FAMILIES.keys())


def get_provider_models(provider: str) -> list:
    """Get available models for a provider (placeholder)"""
    # In production, this would query the provider's API
    # For now, return common models per provider type
    
    provider_info = _get_provider_info(provider)
    if not provider_info:
        return []
    
    # Common model mappings
    MODEL_FAMILIES = {
        "openai": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo", "o1-preview", "o1-mini"],
        "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
        "openrouter": ["nousresearch/hermes-3-llama-3.1-70b", "meta-llama/llama-3.1-405b-instruct"],
        "gemini": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"],
        "xai": ["grok-beta", "grok-vision-beta"],
        "moonshot": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        "zhipu": ["glm-4", "glm-4-air", "glm-4-flash"],
        "groq": ["llama-3.1-70b-versatile", "llama-3.1-8b-instant"],
        "deepseek": ["deepseek-chat", "deepseek-coder"],
    }
    
    return MODEL_FAMILIES.get(provider, [])
