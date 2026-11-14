"""
Schemas for MCP (Model Context Protocol) Server Integration.
Enables dynamic multi-server MCP configurations and automatic tool bridging into Tools Gateway.
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from jarvis.tools.schemas import PermissionTier


class MCPTransportType(str, Enum):
    STDIO = "stdio"
    SSE = "sse"
    WEBSOCKET = "websocket"


class MCPServerConfig(BaseModel):
    """Configuration for an external MCP server."""
    server_id: str = Field(..., description="Unique slug for this server (e.g. 'strata-memory')")
    name: str = Field(..., description="Human-readable server name")
    transport: MCPTransportType = Field(default=MCPTransportType.STDIO)
    command: Optional[str] = Field(default=None, description="Executable command for stdio transport")
    args: List[str] = Field(default_factory=list, description="CLI arguments for the command")
    url: Optional[str] = Field(default=None, description="Endpoint URL for SSE or WebSocket transport")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables passed to the process")
    enabled: bool = Field(default=True)
    description: str = Field(default="")
    
    # Custom tool security overrides: tool_name -> PermissionTier
    security_overrides: Dict[str, PermissionTier] = Field(default_factory=dict)
    # Explicit tools requiring human approval: tool_name -> bool
    approval_overrides: Dict[str, bool] = Field(default_factory=dict)


class MCPRegistryConfig(BaseModel):
    """Container for all configured MCP servers."""
    servers: Dict[str, MCPServerConfig] = Field(default_factory=dict)
