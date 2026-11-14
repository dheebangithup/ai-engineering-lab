"""
Schemas for the J.A.R.V.I.S. Tools Gateway.
Defines ToolDefinition, ToolResult, PermissionTier, and PermissionRequest structures.
"""

from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field


class PermissionTier(str, Enum):
    """Security classification tier for tools."""
    SAFE = "safe"              # Read-only operations, zero side-effects (e.g. read_file, recall)
    SENSITIVE = "sensitive"    # State mutations that can be audited/undone (e.g. write_file, ingest)
    DANGEROUS = "dangerous"    # Irreversible, destructive, or system execution (e.g. run_command, delete)


class ToolParameter(BaseModel):
    """Specification of an individual tool parameter."""
    type: str = "string"       # string, integer, number, boolean, array, object
    description: str = ""
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None


class ToolDefinition(BaseModel):
    """Public specification of a tool exposed to agents."""
    tool_id: str = Field(..., description="Unique slug for the tool (e.g. 'read_file')")
    name: str = Field(..., description="Human-readable tool title")
    description: str = Field(..., description="Natural language description of capabilities")
    category: str = Field(default="general", description="Tool category e.g. filesystem, shell, web, memory")
    parameters: Dict[str, ToolParameter] = Field(default_factory=dict)
    permission_tier: PermissionTier = Field(default=PermissionTier.SAFE)
    requires_approval: bool = False

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert parameter specification to JSON Schema format compatible with LLMs."""
        properties = {}
        required = []
        for param_name, param in self.parameters.items():
            prop: Dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default
            properties[param_name] = prop

            if param.required:
                required.append(param_name)

        return {
            "type": "function",
            "function": {
                "name": self.tool_id,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


class ToolResult(BaseModel):
    """Standardized output from any tool execution."""
    tool_id: str
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    permission_denied: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PermissionRequest(BaseModel):
    """Challenge payload for tools requiring human approval."""
    tool_id: str
    tool_name: str
    permission_tier: PermissionTier
    arguments: Dict[str, Any]
    reason: str = "Tool requires authorization before execution"
