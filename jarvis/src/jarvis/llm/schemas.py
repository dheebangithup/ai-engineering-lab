"""
Standardized schemas for LLM requests, responses, tool calls, and provider health.
Decouples LLM callers from vendor-specific payloads.
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolCallFunction(BaseModel):
    name: str
    arguments: str  # JSON-encoded string or raw arguments


class ToolCallRequest(BaseModel):
    id: str
    type: Literal["function"] = "function"
    function: ToolCallFunction


class LLMMessage(BaseModel):
    role: MessageRole
    content: Optional[str] = ""
    name: Optional[str] = None
    tool_calls: Optional[List[ToolCallRequest]] = None
    tool_call_id: Optional[str] = None


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMResponse(BaseModel):
    """Standardized completion response from any provider in the Provider Gateway."""
    content: str
    role: MessageRole = MessageRole.ASSISTANT
    tool_calls: Optional[List[ToolCallRequest]] = None
    usage: TokenUsage = Field(default_factory=TokenUsage)
    provider_id: str
    model_id: str
    fallback_occurred: bool = False
    failover_history: List[str] = Field(default_factory=list)
    raw_response: Optional[Dict[str, Any]] = None


class ProviderStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class ProviderHealth(BaseModel):
    provider_id: str
    status: ProviderStatus = ProviderStatus.UNKNOWN
    latency_ms: Optional[float] = None
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    available_models: List[str] = Field(default_factory=list)
