"""
Schemas for the J.A.R.V.I.S. Agent Hub.
Defines agent requests, execution steps, and standardized agent responses.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from jarvis.prompts.schemas import PromptContext
from jarvis.tools.schemas import ToolResult


class ExecutionStep(BaseModel):
    """An individual reasoning and action step in an agent's execution trace."""
    step_number: int
    thought: str = ""
    action_tool: Optional[str] = None
    action_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[ToolResult] = None
    observation: str = ""


class AgentRequest(BaseModel):
    """Execution request passed to an agent archetype."""
    query: str
    context: PromptContext
    max_iterations: int = Field(default=8, ge=1, le=25)
    temperature: Optional[float] = None
    preferred_provider: Optional[str] = None
    model_override: Optional[str] = None


class AgentResponse(BaseModel):
    """Standardized response produced by any J.A.R.V.I.S. agent."""
    answer: str
    agent_template: str
    steps: List[ExecutionStep] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    tool_results: List[Dict[str, Any]] = Field(default_factory=list)
    pending_permission: Optional[Dict[str, Any]] = None
    provider_used: str = ""
    model_used: str = ""
    fallback_occurred: bool = False
    failover_history: List[str] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    success: bool = Field(default=True, description="True if agent completed objective successfully")
    error: Optional[str] = Field(default=None, description="Failure reason or error trace for evolutionary feedback")
