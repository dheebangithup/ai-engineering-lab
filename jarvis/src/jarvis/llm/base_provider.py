"""
Abstract Base Provider interface for the Provider Gateway.
Every LLM provider (OpenAI-compatible, Ollama, Groq, Anthropic, etc.) implements this contract.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from jarvis.config.provider_config import ModelRole, ModelSpec, ProviderInstanceConfig
from jarvis.llm.schemas import LLMMessage, LLMResponse, ProviderHealth


class BaseLLMProvider(ABC):
    """Abstract interface for LLM backends in the Provider Gateway."""

    def __init__(self, config: ProviderInstanceConfig):
        self.config = config
        self.provider_id = config.provider_id
        self.health = ProviderHealth(provider_id=self.provider_id)

    @abstractmethod
    async def complete(
        self,
        messages: List[LLMMessage],
        model_id: Optional[str] = None,
        role: Optional[ModelRole] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Execute a text completion or tool call generation."""
        pass

    @abstractmethod
    async def check_health(self) -> ProviderHealth:
        """Check the status and responsiveness of the provider."""
        pass

    def resolve_model_for_role(self, role: ModelRole) -> Optional[str]:
        """Find the best-fitting configured model for this provider given a role."""
        for m_id, spec in self.config.models.items():
            if role in spec.roles:
                return spec.model_id
        # Fallback to the first available model if any exists
        if self.config.models:
            return next(iter(self.config.models.values())).model_id
        return None
