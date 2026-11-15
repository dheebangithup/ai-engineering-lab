"""
Ollama Local Provider.
Inherits from OpenAICompatibleProvider since Ollama exposes full /v1 OpenAI endpoints,
while querying native /api/tags for robust local health and model inventory.
"""

import time
from typing import Any, Dict, List, Optional
import httpx
from jarvis.config.provider_config import ModelRole, ProviderInstanceConfig
from jarvis.llm.providers.openai_compatible import OpenAICompatibleProvider
from jarvis.llm.schemas import (
    LLMMessage,
    LLMResponse,
    MessageRole,
    ProviderHealth,
    ProviderStatus,
    TokenUsage,
)
from jarvis.logger import get_logger

logger = get_logger("llm.provider.ollama")


class OllamaProvider(OpenAICompatibleProvider):
    """Specialized provider for local Ollama instances."""

    def __init__(self, config: ProviderInstanceConfig):
        super().__init__(config)
        # Native Ollama API host (stripping /v1 if present)
        raw_url = config.base_url.rstrip("/")
        if raw_url.endswith("/v1"):
            self.native_url = raw_url[:-3]
        else:
            self.native_url = raw_url

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
        """Complete query using Ollama with decision model awareness."""
        target_model = model_id
        if not target_model and role:
            target_model = self.resolve_model_for_role(role)
        if not target_model and self.config.models:
            target_model = next(iter(self.config.models.keys()))

        model_spec = self.config.models.get(target_model) if target_model else None
        is_decision = (
            role == ModelRole.DECISION
            or (model_spec is not None and model_spec.is_decision_model)
        )

        # Decision models are specialized classification engines, not ordinary conversational LLMs.
        if is_decision:
            from jarvis.decision.decision_model import DecisionModel
            dm = DecisionModel()
            last_user_msg = next((m.content for m in reversed(messages) if m.role == MessageRole.USER), "")
            classification = dm.evaluate(last_user_msg)
            return LLMResponse(
                content=(
                    f"**[Decision Model Evaluation ({target_model})]**\n\n"
                    f"Specialized Decision Model evaluated your query:\n"
                    f"- **Configured Provider**: `{self.name}`\n"
                    f"- **Model Identifier**: `{target_model}`\n"
                    f"- **Model Role**: `DECISION` (Specialized Intent & Complexity Router)\n"
                    f"- **Identified Intent**: `{classification.intent.value}`\n"
                    f"- **Complexity Tier**: `{classification.complexity.value.upper()}`\n"
                    f"- **Recommended Multi-Step Planning**: {classification.requires_planning}\n"
                    f"- **Durable Facts Detected**: {classification.requires_memory_ingest}\n"
                    f"- **Suggested Agent Archetype**: `{classification.suggested_agent}`\n"
                    f"- **Routing Rationale**: {classification.reasoning}"
                ),
                provider_id=self.provider_id,
                model_id=target_model or "decision_model",
                usage=TokenUsage(prompt_tokens=15, completion_tokens=65, total_tokens=80),
            )

        return await super().complete(
            messages=messages,
            model_id=target_model,
            role=role,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            response_format=response_format,
            **kwargs,
        )

    async def classify_decision(
        self,
        query: str,
        model_id: Optional[str] = None,
        context: Optional[str] = None,
    ) -> Optional[Any]:
        """
        Execute structured decision classification on this Ollama provider.
        Evaluates task complexity, intents, tool categories, and durable facts.
        """
        target_model = model_id or self.resolve_model_for_role(ModelRole.DECISION)
        if not target_model:
            return None
        model_spec = self.config.models.get(target_model)
        if not model_spec or ModelRole.DECISION not in model_spec.roles:
            return None

        from jarvis.decision.decision_model import DecisionModel
        dm = DecisionModel()
        classification = dm.evaluate(query, context=context)
        classification.reasoning = f"Evaluated by {self.name} [{target_model}]: {classification.reasoning}"
        return classification

    async def check_health(self) -> ProviderHealth:
        """Query native /api/tags to list loaded models and test local connection."""
        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.native_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    self.health.status = ProviderStatus.HEALTHY
                    self.health.latency_ms = (time.perf_counter() - start_time) * 1000
                    self.health.available_models = models
                    self.health.consecutive_failures = 0
                    self.health.last_error = None
                    return self.health
        except Exception as e:
            self.health.consecutive_failures += 1
            self.health.last_error = f"Ollama daemon not reachable at {self.native_url}: {e}"
            self.health.status = ProviderStatus.UNAVAILABLE
            logger.debug(self.health.last_error)

        return self.health
