"""
LLM abstraction layer for Webis.

Provides a unified interface for interacting with various LLM providers,
with built-in support for:
- Multiple model providers (OpenAI, Claude, DeepSeek, Ollama)
- Automatic fallback chains
- Response caching
- Token counting and cost tracking
- Rate limiting
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


def _has_real_env_value(env_name: str) -> bool:
    """Return True if env var exists and does not look like a placeholder."""
    value = os.environ.get(env_name, "").strip()
    if not value:
        return False

    lowered = value.lower()
    placeholder_values = {
        "your-openai-api-key-here",
        "your-anthropic-api-key-here",
        "your-deepseek-api-key-here",
        "your-serpapi-key-here",
        "your-exa-api-key-here",
        "your-firecrawl-api-key-here",
        "your-secret-key-here-change-this-in-production",
        "your-encryption-key-here",
    }
    if lowered in placeholder_values:
        return False

    # Common placeholder patterns found in env examples.
    if lowered.startswith("sk-your-"):
        return False
    if lowered.startswith("your-") and lowered.endswith("-here"):
        return False

    return True


@dataclass
class LLMResponse:
    """Response from an LLM call."""
    
    content: str
    model: str
    
    # Token usage
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    # Cost (USD)
    cost: float = 0.0
    
    # Timing
    latency_ms: float = 0.0
    
    # Raw response for debugging
    raw: Optional[Dict[str, Any]] = None
    
    # Cache info
    cached: bool = False


@dataclass
class ModelConfig:
    """Configuration for an LLM model."""
    
    name: str
    provider: str  # openai, anthropic, deepseek, ollama, etc.
    
    # API settings
    api_key_env: str = ""
    base_url: Optional[str] = None
    base_url_env: Optional[str] = None
    
    # Model parameters
    temperature: float = 0.0
    max_tokens: int = 4096
    top_p: float = 1.0
    
    # Cost per 1M tokens (USD)
    cost_per_1m_input: float = 0.0
    cost_per_1m_output: float = 0.0
    
    # Capabilities
    supports_json_mode: bool = False
    supports_vision: bool = False
    context_window: int = 4096


# Pre-configured models
BUILTIN_MODELS: Dict[str, ModelConfig] = {
    "deepseek-v3.2": ModelConfig(
        name="deepseek-chat",
        provider="deepseek",
        api_key_env="DEEPSEEK_API_KEY",
        base_url_env="DEEPSEEK_BASE_URL",
        base_url="https://api.deepseek.com",
        cost_per_1m_input=0.14, # Official pricing (approx)
        cost_per_1m_output=0.28, # Official pricing (approx)
        context_window=64000,
        supports_json_mode=True,
    ),
    "deepseek-r1": ModelConfig(
        name="deepseek-reasoner",
        provider="deepseek",
        api_key_env="DEEPSEEK_API_KEY",
        base_url_env="DEEPSEEK_BASE_URL",
        base_url="https://api.deepseek.com",
        cost_per_1m_input=0.55, # Official pricing
        cost_per_1m_output=2.19, # Official pricing
        context_window=64000,
    ),
    "qwen-coder-32b": ModelConfig(
        name="Qwen/Qwen2.5-Coder-32B-Instruct",
        provider="siliconflow",
        api_key_env="SILICONFLOW_API_KEY",
        base_url_env="SILICONFLOW_BASE_URL",
        base_url="https://api.siliconflow.cn/v1",
        cost_per_1m_input=1.26,
        cost_per_1m_output=1.26,
        context_window=32000,
        supports_json_mode=True,
    ),
    "gpt-4o": ModelConfig(
        name="gpt-4o",
        provider="openai",
        api_key_env="OPENAI_API_KEY",
        cost_per_1m_input=2.5,
        cost_per_1m_output=10.0,
        context_window=128000,
        supports_json_mode=True,
        supports_vision=True,
    ),
    "gpt-4o-mini": ModelConfig(
        name="gpt-4o-mini",
        provider="openai",
        api_key_env="OPENAI_API_KEY",
        cost_per_1m_input=0.15,
        cost_per_1m_output=0.6,
        context_window=128000,
        supports_json_mode=True,
    ),
    "claude-sonnet": ModelConfig(
        name="claude-sonnet-4-20250514",
        provider="anthropic",
        api_key_env="ANTHROPIC_API_KEY",
        cost_per_1m_input=3.0,
        cost_per_1m_output=15.0,
        context_window=200000,
        supports_vision=True,
    ),
}


class LLMProvider(ABC):
    """Base class for LLM providers."""
    
    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        **kwargs
    ) -> LLMResponse:
        """Send a chat completion request."""
        raise NotImplementedError


class OpenAICompatibleProvider(LLMProvider):
    """Provider for OpenAI-compatible APIs (OpenAI, SiliconFlow, etc.)."""
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        **kwargs
    ) -> LLMResponse:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package required: pip install openai")
        
        api_key = os.getenv(model_config.api_key_env)
        if not api_key:
            raise ValueError(f"Missing API key: {model_config.api_key_env}")
            
        base_url = model_config.base_url
        if model_config.base_url_env:
            env_url = os.getenv(model_config.base_url_env)
            if env_url:
                base_url = env_url
        
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        
        start_time = time.time()
        
        response = client.chat.completions.create(
            model=model_config.name,
            messages=messages,
            temperature=kwargs.get("temperature", model_config.temperature),
            max_tokens=kwargs.get("max_tokens", model_config.max_tokens),
            top_p=kwargs.get("top_p", model_config.top_p),
        )
        
        latency = (time.time() - start_time) * 1000
        
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        
        # Calculate cost
        cost = (
            (prompt_tokens / 1_000_000) * model_config.cost_per_1m_input +
            (completion_tokens / 1_000_000) * model_config.cost_per_1m_output
        )
        
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=model_config.name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost=cost,
            latency_ms=latency,
            raw=response.model_dump() if hasattr(response, "model_dump") else None,
        )


class ResponseCache:
    """Simple in-memory cache for LLM responses."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: Dict[str, LLMResponse] = {}
    
    def _hash_key(self, messages: List[Dict[str, str]], model: str) -> str:
        content = json.dumps({"messages": messages, "model": model}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def get(self, messages: List[Dict[str, str]], model: str) -> Optional[LLMResponse]:
        key = self._hash_key(messages, model)
        response = self._cache.get(key)
        if response:
            response.cached = True
        return response
    
    def set(self, messages: List[Dict[str, str]], model: str, response: LLMResponse) -> None:
        if len(self._cache) >= self.max_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        key = self._hash_key(messages, model)
        self._cache[key] = response
    
    def clear(self) -> None:
        self._cache.clear()


class LLMRouter:
    """
    Intelligent LLM router with fallback support.
    
    Example:
        >>> router = LLMRouter()
        >>> router.add_model("deepseek-v3.2", primary=True)
        >>> router.add_model("gpt-4o-mini", fallback=True)
        >>> response = router.chat([{"role": "user", "content": "Hello"}])
    """
    
    def __init__(self, enable_cache: bool = True):
        self._models: Dict[str, ModelConfig] = {}
        self._primary_model: Optional[str] = None
        self._fallback_chain: List[str] = []
        
        self._providers: Dict[str, LLMProvider] = {
            "openai": OpenAICompatibleProvider(),
            "siliconflow": OpenAICompatibleProvider(),
            "deepseek": OpenAICompatibleProvider(),
        }
        
        self._cache = ResponseCache() if enable_cache else None
        
        # Usage tracking
        self.total_tokens = 0
        self.total_cost = 0.0
    
    def add_model(
        self,
        model_name: str,
        config: Optional[ModelConfig] = None,
        primary: bool = False,
        fallback: bool = False,
    ) -> "LLMRouter":
        """
        Add a model to the router.
        
        Args:
            model_name: Model identifier (e.g., "deepseek-v3.2")
            config: Model configuration (uses builtin if not provided)
            primary: Set as primary model
            fallback: Add to fallback chain
        """
        if config is None:
            if model_name not in BUILTIN_MODELS:
                raise ValueError(f"Unknown model: {model_name}")
            config = BUILTIN_MODELS[model_name]
        
        self._models[model_name] = config
        
        if primary:
            self._primary_model = model_name
        if fallback:
            self._fallback_chain.append(model_name)
        
        return self
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        use_cache: bool = True,
        **kwargs
    ) -> LLMResponse:
        """
        Send a chat request.
        
        Args:
            messages: Chat messages
            model: Specific model to use (uses primary if not specified)
            use_cache: Whether to use response cache
            **kwargs: Additional parameters for the model
        """
        model_name = model or self._primary_model
        if not model_name:
            raise ValueError("No model specified and no primary model set")
        
        # Check cache
        if use_cache and self._cache:
            cached = self._cache.get(messages, model_name)
            if cached:
                logger.debug(f"Cache hit for {model_name}")
                return cached
        
        # Try primary model, then fallbacks
        models_to_try = [model_name] + [m for m in self._fallback_chain if m != model_name]

        print(models_to_try)
        
        last_error = None
        for try_model in models_to_try:
            config = self._models.get(try_model)
            if not config:
                continue
            
            provider = self._providers.get(config.provider)
            if not provider:
                logger.warning(f"No provider for {config.provider}")
                continue
            
            try:
                response = provider.chat(messages, config, **kwargs)
                
                # Update tracking
                self.total_tokens += response.total_tokens
                self.total_cost += response.cost
                
                # Cache the response
                if use_cache and self._cache:
                    self._cache.set(messages, try_model, response)

                print("success try model: ", try_model)
                
                return response
                
            except Exception as e:
                last_error = e
                logger.warning(f"Model {try_model} failed: {e}")
                continue
        
        raise RuntimeError(f"All models failed. Last error: {last_error}")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost, 4),
        }
    
    def reset_stats(self) -> None:
        """Reset usage statistics."""
        self.total_tokens = 0
        self.total_cost = 0.0


# Default router instance
_default_router: Optional[LLMRouter] = None


def get_default_router() -> LLMRouter:
    """Get the default LLM router with common models configured."""
    global _default_router
    if _default_router is None:
        _default_router = LLMRouter()
        
        if _has_real_env_value("CUSTOM_API_KEY"):
            # Add custom model dynamically
            custom_name = os.environ.get("CUSTOM_MODEL_NAME", "custom-model")
            custom_config = ModelConfig(
                name=custom_name,
                provider="openai",
                api_key_env="CUSTOM_API_KEY",
                base_url=os.environ.get("CUSTOM_BASE_URL"),
                base_url_env="CUSTOM_BASE_URL",
                cost_per_1m_input=0.1,
                cost_per_1m_output=0.1,
                context_window=100000,
                supports_json_mode=True,
            )
            # Register it
            _default_router.add_model(custom_name, config=custom_config, primary=True)
            logger.info(f"Using Custom LLM: {custom_name}")
        else:
            # Auto-select providers by available non-placeholder API keys.
            # Priority: SiliconFlow -> DeepSeek -> OpenAI -> Anthropic
            candidate_order = [
                "qwen-coder-32b",
                "deepseek-v3.2",
                "gpt-4o-mini",
                "claude-sonnet",
            ]
            available_models = [
                model_name
                for model_name in candidate_order
                if _has_real_env_value(BUILTIN_MODELS[model_name].api_key_env)
            ]

            if available_models:
                _default_router.add_model(available_models[0], primary=True)
                for fallback_model in available_models[1:]:
                    _default_router.add_model(fallback_model, fallback=True)
                logger.info(
                    "Auto-selected LLM chain: primary=%s, fallbacks=%s",
                    available_models[0],
                    available_models[1:],
                )
            else:
                # Keep backward-compatible defaults when no valid key is found.
                _default_router.add_model("deepseek-v3.2", primary=True)
                _default_router.add_model("gpt-4o-mini", fallback=True)
                logger.warning(
                    "No valid LLM API keys detected. Using legacy default chain: "
                    "deepseek-v3.2 -> gpt-4o-mini"
                )
            
    return _default_router


__all__ = [
    "LLMResponse",
    "ModelConfig",
    "BUILTIN_MODELS",
    "LLMProvider",
    "OpenAICompatibleProvider",
    "ResponseCache",
    "LLMRouter",
    "get_default_router",
]
