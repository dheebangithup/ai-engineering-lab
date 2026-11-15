"""
Dynamic Provider Store.
Manages persistent provider settings in JSON format (e.g. workspace/settings/providers.json).
Allows runtime additions, removals, updates, and fallback chain customization (ready for Settings UI).
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from jarvis.config.provider_config import (
    ModelRole,
    ModelSpec,
    ProviderInstanceConfig,
    ProviderKind,
    ProviderRegistryConfig,
)
from jarvis.config.settings import get_settings
from jarvis.logger import get_logger
from jarvis.workspace import get_workspace

logger = get_logger("config.provider_store")


class ProviderStore:
    """Manages reading, writing, and seeding provider configurations."""

    def __init__(self, settings_file: Optional[Path] = None):
        if settings_file is None:
            self.settings_file = get_workspace().providers_config_path
        else:
            self.settings_file = Path(settings_file)
        
        self._config: Optional[ProviderRegistryConfig] = None

    def load_config(self, force_reload: bool = False) -> ProviderRegistryConfig:
        """Load provider config from file, or initialize with seed defaults if not found."""
        if self._config is not None and not force_reload:
            return self._config

        if self.settings_file.exists():
            try:
                raw_data = json.loads(self.settings_file.read_text(encoding="utf-8"))
                self._config = ProviderRegistryConfig.model_validate(raw_data)
                logger.info(f"Loaded provider configuration from {self.settings_file}")
                return self._config
            except Exception as e:
                logger.error(f"Failed to parse {self.settings_file}, creating seed config: {e}")

        # Seed with initial providers based on environment/defaults
        self._config = self._create_seed_config()
        self.save_config(self._config)
        return self._config

    def save_config(self, config: ProviderRegistryConfig) -> None:
        """Persist provider configuration to the settings file."""
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings_file.write_text(
            config.model_dump_json(indent=2),
            encoding="utf-8"
        )
        self._config = config
        logger.info(f"Saved provider configuration to {self.settings_file}")

    def add_or_update_provider(self, provider: ProviderInstanceConfig) -> None:
        """Add or update a provider configuration at runtime."""
        cfg = self.load_config(force_reload=True)
        cfg.providers[provider.provider_id] = provider
        self.save_config(cfg)

    def remove_provider(self, provider_id: str) -> bool:
        """Remove a provider and clean up fallback chains."""
        cfg = self.load_config(force_reload=True)
        if provider_id not in cfg.providers:
            return False

        del cfg.providers[provider_id]
        # Remove from fallback chains
        for role, chain in cfg.fallback_chains.items():
            if provider_id in chain:
                cfg.fallback_chains[role] = [p for p in chain if p != provider_id]

        self.save_config(cfg)
        return True

    def set_fallback_chain(self, role: ModelRole, provider_ids: List[str]) -> None:
        """Update the fallback chain order for a specific role."""
        cfg = self.load_config(force_reload=True)
        cfg.fallback_chains[role] = provider_ids
        self.save_config(cfg)

    def _create_seed_config(self) -> ProviderRegistryConfig:
        """Create seed configurations using detected environment values."""
        settings = get_settings()
        providers: Dict[str, ProviderInstanceConfig] = {}

        # 1. KodeKloud OpenAI-compatible provider
        if settings.kodekloud_api_key or True:
            providers["kodekloud"] = ProviderInstanceConfig(
                provider_id="kodekloud",
                name="KodeKloud AI (OpenAI Compatible)",
                kind=ProviderKind.OPENAI_COMPATIBLE,
                base_url=settings.kodekloud_base_url,
                api_key=settings.kodekloud_api_key or "",
                priority=10,
                models={
                    "typesafe/jev-1.13.0": ModelSpec(
                        model_id="typesafe/jev-1.13.0",
                        roles=[ModelRole.DECISION],
                        max_tokens=1024,
                    ),
                    "qwen/qwen3.8-flash": ModelSpec(
                        model_id="qwen/qwen3.8-flash",
                        roles=[ModelRole.FAST, ModelRole.DECISION],
                        max_tokens=4096,
                    ),
                    "gpt-6-luna": ModelSpec(
                        model_id="gpt-6-luna",
                        roles=[ModelRole.REASONING, ModelRole.FAST],
                        max_tokens=8192,
                    ),
                    "gpt-oss-120b": ModelSpec(
                        model_id="gpt-oss-120b",
                        roles=[ModelRole.REASONING, ModelRole.FAST],
                        max_tokens=4096,
                    ),
                },
                enabled=bool(settings.kodekloud_api_key),
            )

        # 2. Ollama Local provider
        providers["ollama_local"] = ProviderInstanceConfig(
            provider_id="ollama_local",
            name="Ollama Local Daemon",
            kind=ProviderKind.OLLAMA,
            base_url=settings.ollama_base_url,
            api_key=settings.ollama_api_key,
            priority=20,
            models={
                "laya:latest": ModelSpec(
                    model_id="laya:latest",
                    roles=[ModelRole.DECISION],
                    max_tokens=512,
                    context_window=512,
                    supports_tools=False,
                ),
                "qwen3:8b": ModelSpec(
                    model_id="qwen3:8b",
                    roles=[ModelRole.FAST, ModelRole.REASONING],
                    max_tokens=4096,
                ),
                "nomic-embed-text": ModelSpec(
                    model_id="nomic-embed-text:latest",
                    roles=[ModelRole.EMBEDDING],
                    max_tokens=2048,
                ),
            },
            enabled=True,
        )

        # 3. Groq provider
        if settings.groq_api_key:
            providers["groq"] = ProviderInstanceConfig(
                provider_id="groq",
                name="Groq Cloud Inference",
                kind=ProviderKind.GROQ,
                base_url=settings.groq_base_url,
                api_key=settings.groq_api_key,
                priority=15,
                models={
                    "llama-3.3-70b-versatile": ModelSpec(
                        model_id="llama-3.3-70b-versatile",
                        roles=[ModelRole.REASONING, ModelRole.FAST],
                        max_tokens=4096,
                    ),
                    "llama-3.1-8b-instant": ModelSpec(
                        model_id="llama-3.1-8b-instant",
                        roles=[ModelRole.DECISION, ModelRole.FAST],
                        max_tokens=2048,
                    ),
                },
                enabled=True,
            )

        # Fallback chains (Primary -> Secondary -> Tertiary)
        fallback_chains: Dict[ModelRole, List[str]] = {
            ModelRole.DECISION: ["kodekloud", "ollama_local"],
            ModelRole.FAST: ["kodekloud", "ollama_local"],
            ModelRole.REASONING: ["kodekloud", "ollama_local"],
            ModelRole.EMBEDDING: ["ollama_local"],
        }

        return ProviderRegistryConfig(
            providers=providers,
            fallback_chains=fallback_chains,
            default_role=ModelRole.FAST,
        )
