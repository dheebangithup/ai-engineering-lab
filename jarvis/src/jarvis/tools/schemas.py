from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DefaultToolId(str, Enum):
    """Standard IDs for built-in JARVIS tools."""
    LIST_FILES = "list_files"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    SEARCH_FILES = "search_files"
    RUN_COMMAND = "run_command"


class TraceEventType(str, Enum):
    """Event types recorded in execution traces."""
    TOOL_START = "tool_start"
    TOOL_STARTED = "tool_started"
    TOOL_END = "tool_end"
    TOOL_COMPLETED = "tool_completed"
    TOOL_ERROR = "tool_error"
    EXECUTOR_ERROR = "executor_error"
    FATAL_ERROR = "fatal_error"


HUMAN_INPUT_INDICATOR: str = "NEED_HUMAN_INPUT:"


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

