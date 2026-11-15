"""
Schemas for the J.A.R.V.I.S. Core Orchestration Pipeline.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from jarvis.agents.schemas import AgentResponse, ExecutionStep
from jarvis.decision.schemas import TaskClassification


class PendingAction(BaseModel):
    """Payload representing a tool execution that is awaiting human approval."""
    action_token: str
    tool_id: str
    tool_name: str = ""
    permission_tier: str = "dangerous"
    arguments: Dict[str, Any] = Field(default_factory=dict)
    reason: str = ""
    created_at: float = 0.0


class JarvisSession(BaseModel):
    """Conversation session tracking history and context."""
    session_id: str = "default"
    history: List[Dict[str, str]] = Field(default_factory=list)
    pending_action: Optional[PendingAction] = None


class JarvisRequest(BaseModel):
    """User input request to J.A.R.V.I.S."""
    query: str
    session_id: str = "default"
    stream: bool = False
    context_override: Optional[str] = None
    preferred_provider: Optional[str] = None
    model_override: Optional[str] = None


class JarvisResponse(BaseModel):
    """Complete output returned by J.A.R.V.I.S."""
    query: str
    answer: str
    classification: TaskClassification
    agent_used: str
    tools_used: List[str] = Field(default_factory=list)
    tool_results: List[Dict[str, Any]] = Field(default_factory=list)
    steps: List[ExecutionStep] = Field(default_factory=list)
    pending_permission: Optional[Dict[str, Any]] = None
    provider_used: str = ""
    model_used: str = ""
    fallback_occurred: bool = False
    failover_history: List[str] = Field(default_factory=list)
    execution_time_ms: float = 0.0
