"""
Configuration schemas for the Provider Gateway.
Supports dynamic multi-provider configuration, model roles, and fallback chains.
"""

from enum import Enum
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class ModelRole(str, Enum):
    """System roles assigned to models."""
    DECISION = "decision"       # Fast, structured, low-latency (for complexity/routing)
    FAST = "fast"               # Lightweight tasks, basic tool synthesis
    REASONING = "reasoning"     # Heavy reasoning, multi-step planning, coding
    EMBEDDING = "embedding"     # Text embedding generation


class ProviderKind(str, Enum):
    """Underlying provider protocol."""
    OPENAI_COMPATIBLE = "openai_compatible"
    OLLAMA = "ollama"
    GROQ = "groq"


class ModelSpec(BaseModel):
    """Specification of an individual model provided by an endpoint."""
    model_id: str = Field(..., description="Actual model identifier on the remote or local service")
    roles: List[ModelRole] = Field(default_factory=lambda: [ModelRole.FAST])
    max_tokens: int = Field(default=4096, ge=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    supports_tools: bool = Field(default=True)
    supports_vision: bool = Field(default=False)
    context_window: int = Field(default=8192)

    @property
    def is_decision_model(self) -> bool:
        """True if model is configured as a dedicated Decision model."""
        return ModelRole.DECISION in self.roles and ModelRole.REASONING not in self.roles and ModelRole.FAST not in self.roles


class ProviderInstanceConfig(BaseModel):
    """Configuration for a specific provider instance."""
    provider_id: str = Field(..., description="Unique slug for this provider configuration (e.g. 'kodekloud', 'ollama_local')")
    name: str = Field(..., description="Human-readable provider name")
    kind: ProviderKind = Field(default=ProviderKind.OPENAI_COMPATIBLE)
    base_url: str = Field(..., description="Base URL of the provider API endpoint")
    api_key: str = Field(default="", description="API key or token if authentication is required")
    models: Dict[str, ModelSpec] = Field(default_factory=dict, description="Configured models for this provider")
    enabled: bool = Field(default=True)
    timeout_seconds: float = Field(default=60.0, ge=1.0)
    max_retries: int = Field(default=1, ge=0)
    priority: int = Field(default=10, description="Lower number = higher priority")
    custom_headers: Dict[str, str] = Field(default_factory=dict)


class FallbackRoute(BaseModel):
    """Defines prioritized provider failover for a specific role."""
    role: ModelRole
    provider_ids: List[str] = Field(
        default_factory=list,
        description="Ordered list of provider IDs. If the first fails, it falls back to the next."
    )


class ProviderRegistryConfig(BaseModel):
    """Root configuration holding all provider instances and fallback routes."""
    providers: Dict[str, ProviderInstanceConfig] = Field(default_factory=dict)
    fallback_chains: Dict[ModelRole, List[str]] = Field(default_factory=dict)
    default_role: ModelRole = Field(default=ModelRole.FAST)
