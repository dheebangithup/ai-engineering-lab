"""
OpenAI-Compatible Provider implementation.
Handles KodeKloud, Groq, Ollama v1 endpoints, and any standard OpenAI chat/completions API.
"""

import time
from typing import Any, Dict, List, Optional
import httpx
from jarvis.config.provider_config import ModelRole, ProviderInstanceConfig
from jarvis.llm.base_provider import BaseLLMProvider
from jarvis.llm.schemas import (
    LLMMessage,
    LLMResponse,
    MessageRole,
    ProviderHealth,
    ProviderStatus,
    TokenUsage,
    ToolCallFunction,
    ToolCallRequest,
)
from jarvis.logger import get_logger

logger = get_logger("llm.provider.openai_compat")


class OpenAICompatibleProvider(BaseLLMProvider):
    """Client for OpenAI-compatible chat completion APIs."""

    def __init__(self, config: ProviderInstanceConfig):
        super().__init__(config)
        self.base_url = config.base_url.rstrip("/")
        headers = {
            "Content-Type": "application/json",
            **config.custom_headers,
        }
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=config.timeout_seconds,
        )

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
        """Call the /chat/completions endpoint."""
        target_model = model_id
        if not target_model and role:
            target_model = self.resolve_model_for_role(role)
        if not target_model:
            if self.config.models:
                target_model = next(iter(self.config.models.keys()))
            else:
                target_model = "gpt-4o"

        model_spec = self.config.models.get(target_model)
        temp = temperature if temperature is not None else (model_spec.temperature if model_spec else 0.7)
        tokens = max_tokens if max_tokens is not None else (model_spec.max_tokens if model_spec else 2048)

        formatted_messages = []
        for m in messages:
            msg_dict: Dict[str, Any] = {"role": m.role.value, "content": m.content or ""}
            if m.name:
                msg_dict["name"] = m.name
            if m.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in m.tool_calls
                ]
            if m.tool_call_id:
                msg_dict["tool_call_id"] = m.tool_call_id
            formatted_messages.append(msg_dict)

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": formatted_messages,
            "temperature": temp,
            "max_tokens": tokens,
        }

        if tools:
            payload["tools"] = tools
        if response_format:
            payload["response_format"] = response_format

        # Add additional kwargs
        payload.update(kwargs)

        start_time = time.perf_counter()
        try:
            url = f"{self.base_url}/chat/completions"
            response = await self._client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            latency = (time.perf_counter() - start_time) * 1000

            choice = data["choices"][0]
            message_data = choice["message"]
            content = message_data.get("content") or ""

            # Parse tool calls if returned
            parsed_tool_calls: Optional[List[ToolCallRequest]] = None
            if "tool_calls" in message_data and message_data["tool_calls"]:
                parsed_tool_calls = []
                for tc in message_data["tool_calls"]:
                    parsed_tool_calls.append(
                        ToolCallRequest(
                            id=tc.get("id", f"call_{len(parsed_tool_calls)}"),
                            type=tc.get("type", "function"),
                            function=ToolCallFunction(
                                name=tc["function"]["name"],
                                arguments=tc["function"]["arguments"]
                                if isinstance(tc["function"]["arguments"], str)
                                else str(tc["function"]["arguments"]),
                            ),
                        )
                    )

            # Parse usage
            usage_data = data.get("usage", {})
            usage = TokenUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

            # Update health
            self.health.status = ProviderStatus.HEALTHY
            self.health.latency_ms = latency
            self.health.consecutive_failures = 0
            self.health.last_error = None

            return LLMResponse(
                content=content,
                role=MessageRole(message_data.get("role", "assistant")),
                tool_calls=parsed_tool_calls,
                usage=usage,
                provider_id=self.provider_id,
                model_id=target_model,
                raw_response=data,
            )

        except Exception as e:
            self.health.consecutive_failures += 1
            self.health.last_error = str(e)
            self.health.status = (
                ProviderStatus.UNAVAILABLE
                if self.health.consecutive_failures >= 3
                else ProviderStatus.DEGRADED
            )
            logger.warning(
                f"Provider '{self.provider_id}' failed on model '{target_model}': {e}"
            )
            raise e

    async def check_health(self) -> ProviderHealth:
        """Check provider connectivity by hitting /models endpoint or simple ping."""
        start_time = time.perf_counter()
        try:
            url = f"{self.base_url}/models"
            resp = await self._client.get(url, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("id", "") for m in data.get("data", []) if "id" in m]
                self.health.status = ProviderStatus.HEALTHY
                self.health.available_models = models
                self.health.latency_ms = (time.perf_counter() - start_time) * 1000
                self.health.last_error = None
                return self.health
        except Exception as e:
            logger.debug(f"Health check /models failed for {self.provider_id}: {e}")

        # Fallback health check if /models not supported: try options or assume degraded
        self.health.status = ProviderStatus.DEGRADED
        return self.health

    async def close(self) -> None:
        """Close underlying HTTP client."""
        await self._client.aclose()
