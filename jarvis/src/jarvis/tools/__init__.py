"""
Tools Gateway module for J.A.R.V.I.S.
"""

from jarvis.tools.decorators import jarvis_tool
from jarvis.tools.meta_tools import create_gateway_meta_tools
from jarvis.tools.permissions import PermissionInterceptor
from jarvis.tools.schemas import (
    PermissionRequest,
    PermissionTier,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from jarvis.tools.tool_discovery import ToolDiscovery
from jarvis.tools.tool_gateway import ToolsGateway
from jarvis.tools.tool_registry import DuplicateToolError, ToolNotFoundError, ToolRegistry

__all__ = [
    "jarvis_tool",
    "create_gateway_meta_tools",
    "PermissionInterceptor",
    "PermissionRequest",
    "PermissionTier",
    "ToolDefinition",
    "ToolParameter",
    "ToolResult",
    "ToolDiscovery",
    "ToolsGateway",
    "DuplicateToolError",
    "ToolNotFoundError",
    "ToolRegistry",
]
