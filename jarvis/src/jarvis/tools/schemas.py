from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ToolDefinition:
    """
    Metadata and specification of a tool exposed to agents.
    Excludes implementation details.
    """
    id: str
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON schema compatible dictionary


@dataclass(frozen=True)
class ToolResult:
    """
    Structured outcome of a tool execution via ToolsGateway.
    """
    tool_id: str
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
