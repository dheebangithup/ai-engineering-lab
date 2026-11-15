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
        self.name = config.name
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

    async def classify_decision(
        self,
        query: str,
        model_id: Optional[str] = None,
        context: Optional[str] = None,
    ) -> Optional[Any]:
        """
        Execute structured decision classification on this provider.
        Decision models are specialized intent & complexity routers, not ordinary generative LLMs.
        """
        return None

    def resolve_model_for_role(self, role: ModelRole) -> Optional[str]:
        """Find the best-fitting configured model for this provider given a role."""
        # 1. Exact match for requested role
        for m_id, spec in self.config.models.items():
            if role in spec.roles:
                return spec.model_id

        # 2. If looking for generative roles (FAST/REASONING), avoid decision-only or embedding-only models
        if role in (ModelRole.FAST, ModelRole.REASONING):
            for m_id, spec in self.config.models.items():
                if any(r in (ModelRole.FAST, ModelRole.REASONING) for r in spec.roles):
                    return spec.model_id

        # 3. If looking for DECISION, look for any model tagged with DECISION
        if role == ModelRole.DECISION:
            for m_id, spec in self.config.models.items():
                if ModelRole.DECISION in spec.roles:
                    return spec.model_id

        # 4. Fallback to first available model if any exists
        if self.config.models:
            return next(iter(self.config.models.values())).model_id
        return None
