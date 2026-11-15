"""
Provider Gateway for J.A.R.V.I.S.
The centralized routing, load-balancing, and fault-tolerant fallback engine for all LLM interactions.
"""

from typing import Any, Dict, List, Optional
from jarvis.config.provider_config import (
    ModelRole,
    ModelSpec,
    ProviderInstanceConfig,
    ProviderKind,
    ProviderRegistryConfig,
)
from jarvis.config.provider_store import ProviderStore
from jarvis.llm.base_provider import BaseLLMProvider
from jarvis.llm.providers.ollama_provider import OllamaProvider
from jarvis.llm.providers.openai_compatible import OpenAICompatibleProvider
from jarvis.llm.schemas import (
    LLMMessage,
    LLMResponse,
    ProviderHealth,
    ProviderStatus,
)
from jarvis.logger import get_logger

logger = get_logger("llm.provider_gateway")


class ProviderGateway:
    """
    Decoupled Provider Gateway.
    Orchestrates multiple LLM providers with automatic cascade failover.
    """

    def __init__(self, store: Optional[ProviderStore] = None):
        self.store = store or ProviderStore()
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._config: Optional[ProviderRegistryConfig] = None
        self.reload()

    def reload(self) -> None:
        """Reload configuration and refresh provider instances."""
        self._config = self.store.load_config(force_reload=True)
        self._providers.clear()

        for pid, p_cfg in self._config.providers.items():
            if not p_cfg.enabled:
                continue
            provider_instance = self._create_provider_instance(p_cfg)
            if provider_instance:
                self._providers[pid] = provider_instance

        logger.info(
            f"ProviderGateway initialized with {len(self._providers)} active providers: {list(self._providers.keys())}"
        )

    def _create_provider_instance(self, config: ProviderInstanceConfig) -> Optional[BaseLLMProvider]:
        """Factory method to instantiate the appropriate provider backend."""
        try:
            if config.kind == ProviderKind.OLLAMA:
                return OllamaProvider(config)
            elif config.kind in (ProviderKind.OPENAI_COMPATIBLE, ProviderKind.GROQ):
                return OpenAICompatibleProvider(config)
            else:
                logger.warning(f"Unknown provider kind '{config.kind}', defaulting to OpenAICompatibleProvider")
                return OpenAICompatibleProvider(config)
        except Exception as e:
            logger.error(f"Failed to instantiate provider '{config.provider_id}': {e}")
            return None

    def get_provider(self, provider_id: str) -> Optional[BaseLLMProvider]:
        """Directly retrieve an initialized provider by ID."""
        return self._providers.get(provider_id)

    def list_active_providers(self) -> List[str]:
        """List provider IDs that are currently active in memory."""
        return list(self._providers.keys())

    def get_fallback_chain_for_role(self, role: ModelRole) -> List[str]:
        """Resolve the ordered chain of provider IDs to attempt for a given role."""
        if not self._config:
            self._config = self.store.load_config()

        chain = self._config.fallback_chains.get(role, [])
        # Filter to only providers that are actually registered and enabled
        active_chain = [pid for pid in chain if pid in self._providers]

        # If active chain is empty, fall back to any active provider that has a model for this role or any active provider
        if not active_chain:
            for pid, prov in self._providers.items():
                if prov.resolve_model_for_role(role) is not None:
                    active_chain.append(pid)
            if not active_chain and self._providers:
                active_chain = list(self._providers.keys())

        return active_chain

    async def classify_decision(
        self,
        query: str,
        context: Optional[str] = None,
    ) -> Optional[Any]:
        """
        Execute structured decision classification across the configured DECISION fallback chain.
        Decision models are specialized intent & complexity routers, not ordinary generative LLMs.
        """
        chain = self.get_fallback_chain_for_role(ModelRole.DECISION)
        for pid in chain:
            provider = self._providers.get(pid)
            if not provider:
                continue
            decision_model = provider.resolve_model_for_role(ModelRole.DECISION)
            if not decision_model:
                continue
            try:
                result = await provider.classify_decision(query, model_id=decision_model, context=context)
                if result is not None:
                    return result
            except Exception as e:
                logger.warning(f"Decision model provider '{pid}' error: {e}. Falling back...")
        return None

    async def complete(
        self,
        messages: List[LLMMessage],
        role: ModelRole = ModelRole.FAST,
        preferred_provider_id: Optional[str] = None,
        model_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Execute completion with automatic fallback across the provider pool.
        """
        chain = []
        if preferred_provider_id and preferred_provider_id in self._providers:
            chain.append(preferred_provider_id)

        # Append role-based fallback chain
        for pid in self.get_fallback_chain_for_role(role):
            if pid not in chain:
                chain.append(pid)

        if not chain:
            raise RuntimeError(
                f"No enabled providers available in ProviderGateway for role '{role}'"
            )

        failover_history: List[str] = []
        last_error: Optional[Exception] = None

        for idx, provider_id in enumerate(chain):
            provider = self._providers.get(provider_id)
            if not provider:
                continue

            # Determine model to use
            target_model = model_id
            if not target_model:
                target_model = provider.resolve_model_for_role(role)

            is_fallback = idx > 0

            try:
                if is_fallback:
                    logger.warning(
                        f"Cascading fallback -> Attempting provider '{provider_id}' with model '{target_model}' for role '{role}'"
                    )

                response = await provider.complete(
                    messages=messages,
                    model_id=target_model,
                    role=role,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                    response_format=response_format,
                    **kwargs,
                )

                # Annotate response with failover tracking
                response.fallback_occurred = is_fallback
                response.failover_history = failover_history
                return response

            except Exception as e:
                err_msg = f"Provider '{provider_id}' failed: {e}"
                logger.warning(err_msg)
                failover_history.append(err_msg)
                last_error = e

        # If all providers in the chain failed
        raise RuntimeError(
            f"All providers in fallback chain failed for role '{role}'. "
            f"Chain: {chain}. Errors: {failover_history}"
        ) from last_error

    def get_providers_health(self) -> Dict[str, ProviderHealth]:
        """Return the current in-memory health status of registered providers without outbound network calls."""
        return {pid: provider.health for pid, provider in self._providers.items()}

    async def check_all_providers_health(self) -> Dict[str, ProviderHealth]:
        """Perform health checks on all registered providers."""
        results: Dict[str, ProviderHealth] = {}
        for pid, provider in self._providers.items():
            results[pid] = await provider.check_health()
        return results

    async def close(self) -> None:
        """Clean up HTTP clients for all providers."""
        for provider in self._providers.values():
            if hasattr(provider, "close"):
                try:
                    await provider.close()
                except Exception:
                    pass
