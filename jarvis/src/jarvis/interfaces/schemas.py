"""
Schemas for the J.A.R.V.I.S. REST API & Web Interfaces.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from jarvis.config.provider_config import ModelRole, ProviderInstanceConfig, ProviderKind
from jarvis.core.schemas import JarvisResponse
from jarvis.decision.schemas import TaskClassification
from jarvis.llm.schemas import ProviderHealth
from jarvis.mcp.schemas import MCPServerConfig
from jarvis.tools.schemas import PermissionTier, ToolDefinition


class ChatRequest(BaseModel):
    query: str
    session_id: str = "default"
    context_override: Optional[str] = None
    preferred_provider: Optional[str] = None
    model_override: Optional[str] = None


class UpdateFallbackChainRequest(BaseModel):
    role: ModelRole
    provider_ids: List[str]


class SystemStatusResponse(BaseModel):
    status: str = "operational"
    workspace_root: str
    active_providers: List[str]
    provider_health: Dict[str, ProviderHealth]
    total_tools: int
    tool_categories: List[str]
    mcp_servers: List[str]


class PermissionApprovalRequest(BaseModel):
    action_token: str
    session_id: str = "default"
    approved: bool


class TestProviderConnectionRequest(BaseModel):
    base_url: str
    api_key: Optional[str] = ""
    kind: ProviderKind = ProviderKind.OPENAI_COMPATIBLE
    model_id: Optional[str] = None
    custom_headers: Dict[str, str] = Field(default_factory=dict)


class TestProviderConnectionResponse(BaseModel):
    success: bool
    status: str  # "connected", "auth_failed", "unreachable", "model_not_found", "error"
    latency_ms: Optional[float] = None
    message: str
    available_models: List[str] = Field(default_factory=list)
    model_capabilities: Dict[str, List[str]] = Field(default_factory=dict)
    http_status_code: Optional[int] = None
