"""
Tools Gateway for J.A.R.V.I.S.
The centralized entry point for deferred tool discovery, schema validation,
permission verification, and sandboxed tool execution.
"""

import inspect
import time
from typing import Any, Callable, Dict, List, Optional
from jarvis.logger import get_logger
from jarvis.tools.permissions import PermissionInterceptor
from jarvis.tools.schemas import PermissionTier, ToolDefinition, ToolResult
from jarvis.tools.tool_discovery import ToolDiscovery
from jarvis.tools.tool_registry import ToolNotFoundError, ToolRegistry

logger = get_logger("tools.gateway")


class ToolsGateway:
    """Centralized Tools Gateway for J.A.R.V.I.S."""

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        permission_interceptor: Optional[PermissionInterceptor] = None,
    ):
        self.registry = registry or ToolRegistry()
        self.discovery = ToolDiscovery(self.registry)
        self.permissions = permission_interceptor or PermissionInterceptor()

    def register_tool(self, tool_fn: Callable) -> None:
        """Register a function decorated with @jarvis_tool."""
        if not hasattr(tool_fn, "_jarvis_tool_def"):
            raise ValueError(f"Function '{tool_fn.__name__}' is missing @jarvis_tool decorator")
        definition: ToolDefinition = getattr(tool_fn, "_jarvis_tool_def")
        if self.registry.get_definition(definition.tool_id):
            return  # Already registered, idempotent
        self.registry.register(definition, tool_fn)

    def discover_tools(
        self,
        query: str,
        category: Optional[str] = None,
        max_results: int = 5,
    ) -> List[ToolDefinition]:
        """Natural-language search over the registry returning relevant tools."""
        return self.discovery.search(query=query, category=category, max_results=max_results)

    def list_tools(self, category: Optional[str] = None) -> List[ToolDefinition]:
        """List tool definitions, optionally filtered by category."""
        return self.registry.list_tools(category=category)

    async def execute_tool(
        self,
        tool_id: str,
        arguments: Optional[Dict[str, Any]] = None,
        bypass_permission: bool = False,
    ) -> ToolResult:
        """
        Execute a tool by ID with schema validation and permission enforcement.
        Always returns a standardized ToolResult.
        """
        args = arguments or {}
        tool_def = self.registry.get_definition(tool_id)
        if not tool_def:
            logger.warning(f"Attempted execution of unknown tool ID '{tool_id}'")
            return ToolResult(
                tool_id=tool_id,
                success=False,
                error=f"Tool '{tool_id}' not found in registry",
            )

        handler = self.registry.get_handler(tool_id)
        if not handler:
            return ToolResult(
                tool_id=tool_id,
                success=False,
                error=f"No execution handler registered for tool '{tool_id}'",
            )

        # 1. Validate required parameters
        missing = [
            p_name
            for p_name, param in tool_def.parameters.items()
            if param.required and p_name not in args
        ]
        if missing:
            return ToolResult(
                tool_id=tool_id,
                success=False,
                error=f"Missing required parameter(s): {', '.join(missing)}",
            )

        # 2. Permission Interceptor check (human-in-the-loop)
        if not bypass_permission:
            allowed = await self.permissions.verify_permission(tool_def, args)
            if not allowed:
                logger.warning(f"Permission denied for tool '{tool_id}'")
                return ToolResult(
                    tool_id=tool_id,
                    success=False,
                    permission_denied=True,
                    error=f"Permission denied: Execution of '{tool_id}' ({tool_def.permission_tier.value}) requires explicit authorization.",
                    data={
                        "tool_id": tool_id,
                        "tool_name": tool_def.name,
                        "permission_tier": tool_def.permission_tier.value,
                        "arguments": args,
                        "reason": f"Tool '{tool_id}' is classified as {tool_def.permission_tier.value.upper()} and requires user approval before execution.",
                    },
                )

        # 3. Sandboxed execution
        start_time = time.perf_counter()
        try:
            if inspect.iscoroutinefunction(handler):
                data = await handler(**args)
            else:
                data = handler(**args)

            duration_ms = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                tool_id=tool_id,
                success=True,
                data=data,
                metadata={"execution_time_ms": round(duration_ms, 2)},
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Error executing tool '{tool_id}': {e}", exc_info=True)
            return ToolResult(
                tool_id=tool_id,
                success=False,
                error=str(e),
                metadata={"execution_time_ms": round(duration_ms, 2)},
            )
