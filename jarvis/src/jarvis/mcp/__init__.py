"""
Model Context Protocol (MCP) Multi-Server Integration for J.A.R.V.I.S.
"""

from jarvis.mcp.bridge import (
    bridge_mcp_server_to_gateway,
    convert_mcp_tool_to_definition,
    determine_permission_tier,
)
from jarvis.mcp.mcp_client import MCPClientWrapper
from jarvis.mcp.mcp_manager import MCPManager
from jarvis.mcp.mcp_store import MCPStore
from jarvis.mcp.schemas import MCPRegistryConfig, MCPServerConfig, MCPTransportType

__all__ = [
    "MCPClientWrapper",
    "MCPManager",
    "MCPStore",
    "MCPServerConfig",
    "MCPRegistryConfig",
    "MCPTransportType",
    "bridge_mcp_server_to_gateway",
    "convert_mcp_tool_to_definition",
    "determine_permission_tier",
]
