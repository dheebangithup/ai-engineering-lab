"""
Gateway Meta-Tools for J.A.R.V.I.S. (The Uber Pattern).
Exposes exactly 3 meta-tools to agents, allowing them to search, inspect,
and execute from thousands of registered tools dynamically at runtime.
"""

from typing import Any, Dict, List, Optional
from jarvis.tools.decorators import jarvis_tool
from jarvis.tools.schemas import PermissionTier, ToolDefinition, ToolParameter, ToolResult
from jarvis.tools.tool_gateway import ToolsGateway


def create_gateway_meta_tools(gateway: ToolsGateway) -> List[Any]:
    """
    Generate the 3 standardized meta-tools bound to a specific ToolsGateway instance.
    These are the ONLY tools exposed to LLM agents.
    """

    @jarvis_tool(
        tool_id="search_tools",
        name="Search Available Tools",
        description="Search for available tools across all categories using natural language keywords.",
        category="meta",
        permission_tier=PermissionTier.SAFE,
        parameters={
            "query": ToolParameter(
                type="string",
                description="Natural language query describing what capability you need (e.g. 'read python file', 'web search')",
                required=True,
            ),
            "category": ToolParameter(
                type="string",
                description="Optional category to filter results (e.g. 'filesystem', 'shell', 'memory', 'web')",
                default=None,
            ),
            "max_results": ToolParameter(
                type="integer",
                description="Maximum number of tools to return",
                default=3,
            ),
        },
    )
    async def search_tools(
        query: str,
        category: Optional[str] = None,
        max_results: int = 3,
    ) -> List[Dict[str, Any]]:
        matching_tools = gateway.discover_tools(query=query, category=category, max_results=max_results)
        return [
            {
                "tool_id": t.tool_id,
                "name": t.name,
                "category": t.category,
                "description": t.description,
                "parameters": {
                    p_name: {
                        "type": p.type,
                        "description": p.description,
                        "required": p.required,
                        "default": p.default,
                    }
                    for p_name, p in t.parameters.items()
                },
                "permission_tier": t.permission_tier.value,
            }
            for t in matching_tools
        ]

    @jarvis_tool(
        tool_id="list_tools",
        name="List Tools by Category",
        description="Browse available tool categories or list all registered tools in a category.",
        category="meta",
        permission_tier=PermissionTier.SAFE,
        parameters={
            "category": ToolParameter(
                type="string",
                description="Category name to browse (e.g. 'filesystem', 'shell', 'memory', 'web'). If omitted, lists all categories.",
                default=None,
            ),
        },
    )
    async def list_tools(category: Optional[str] = None) -> Dict[str, Any]:
        if category:
            tools = gateway.list_tools(category=category)
            return {
                "category": category,
                "tools": [{"tool_id": t.tool_id, "name": t.name, "description": t.description} for t in tools],
            }
        return {
            "available_categories": gateway.registry.list_categories(),
            "total_tools": len(gateway.registry),
        }

    @jarvis_tool(
        tool_id="execute_tool",
        name="Execute Tool",
        description="Execute a specific registered tool by ID with the required arguments.",
        category="meta",
        permission_tier=PermissionTier.SAFE,
        parameters={
            "tool_id": ToolParameter(
                type="string",
                description="The exact tool_id discovered via search_tools (e.g. 'read_file')",
                required=True,
            ),
            "arguments": ToolParameter(
                type="object",
                description="Dictionary of arguments matching the tool's parameter specification",
                default={},
            ),
        },
    )
    async def execute_tool(tool_id: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        result: ToolResult = await gateway.execute_tool(tool_id=tool_id, arguments=arguments)
        return result.model_dump()

    return [search_tools, list_tools, execute_tool]
