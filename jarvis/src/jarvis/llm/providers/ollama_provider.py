"""
Ollama Local Provider.
Inherits from OpenAICompatibleProvider since Ollama exposes full /v1 OpenAI endpoints,
while querying native /api/tags for robust local health and model inventory.
"""

import time
from typing import Optional
import httpx
from jarvis.config.provider_config import ProviderInstanceConfig
from jarvis.llm.providers.openai_compatible import OpenAICompatibleProvider
from jarvis.llm.schemas import ProviderHealth, ProviderStatus
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
