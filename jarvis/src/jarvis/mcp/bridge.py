"""
MCP-to-ToolsGateway Bridge for J.A.R.V.I.S.
Converts external MCP tools into native Jarvis ToolDefinitions, enforces security tiers,
and binds async callables to the central ToolsGateway.
"""

from typing import Any, Callable, Dict, List, Optional
import mcp.types as types
from jarvis.logger import get_logger
from jarvis.mcp.mcp_client import MCPClientWrapper
from jarvis.mcp.schemas import MCPServerConfig
from jarvis.tools.schemas import PermissionTier, ToolDefinition, ToolParameter
from jarvis.tools.tool_gateway import ToolsGateway

logger = get_logger("mcp.bridge")

# Keywords that mandate DANGEROUS tier and explicit user approval
DANGEROUS_ACTION_KEYWORDS = ["delete", "purge", "prune", "edit", "remove", "drop", "destroy"]
SENSITIVE_ACTION_KEYWORDS = ["ingest", "store", "write", "update", "create", "insert"]


def determine_permission_tier(
    tool_name: str,
    server_config: MCPServerConfig,
) -> tuple[PermissionTier, bool]:
    """
    Determine the security classification and approval requirement for an MCP tool.
    Returns: (PermissionTier, requires_approval)
    """
    # 1. Check explicit server configuration overrides first
    if tool_name in server_config.security_overrides:
        tier = server_config.security_overrides[tool_name]
        req_approval = server_config.approval_overrides.get(
            tool_name, tier == PermissionTier.DANGEROUS
        )
        return tier, req_approval

    name_lower = tool_name.lower()

    # 2. Strict Dangerous Rules: delete, purge, prune, edit ALWAYS require permission
    if any(kw in name_lower for kw in DANGEROUS_ACTION_KEYWORDS):
        return PermissionTier.DANGEROUS, True

    # 3. Sensitive Rules
    if any(kw in name_lower for kw in SENSITIVE_ACTION_KEYWORDS):
        req_approval = server_config.approval_overrides.get(tool_name, False)
        return PermissionTier.SENSITIVE, req_approval

    # 4. Safe default (recall, read, get, search, feedback)
    return PermissionTier.SAFE, False


def convert_mcp_tool_to_definition(
    mcp_tool: types.Tool,
    server_config: MCPServerConfig,
    category: Optional[str] = None,
) -> ToolDefinition:
    """Convert an MCP Tool specification into a Jarvis ToolDefinition."""
    tier, requires_approval = determine_permission_tier(mcp_tool.name, server_config)

    # Parse input schema properties (handle both input_schema and inputSchema)
    input_schema = getattr(mcp_tool, "input_schema", None) or getattr(mcp_tool, "inputSchema", {}) or {}
    parameters: Dict[str, ToolParameter] = {}
    properties = input_schema.get("properties", {})
    required_fields = set(input_schema.get("required", []))

    for p_name, p_spec in properties.items():
        parameters[p_name] = ToolParameter(
            type=p_spec.get("type", "string"),
            description=p_spec.get("description", ""),
            required=p_name in required_fields,
            default=p_spec.get("default", None),
            enum=p_spec.get("enum", None),
        )

    cat = category or ("memory" if "memory" in mcp_tool.name or "strata" in server_config.server_id else server_config.server_id)

    return ToolDefinition(
        tool_id=mcp_tool.name,
        name=mcp_tool.name.replace("_", " ").title(),
        description=mcp_tool.description or f"MCP tool '{mcp_tool.name}' from {server_config.name}",
        category=cat,
        permission_tier=tier,
        requires_approval=requires_approval,
        parameters=parameters,
    )


def create_mcp_callable(client: MCPClientWrapper, tool_name: str) -> Callable:
    """Create an async callable handler forwarding arguments to the MCP server."""
    async def mcp_invoker(**kwargs: Any) -> Any:
        return await client.call_tool(tool_name, arguments=kwargs)

    return mcp_invoker


async def bridge_mcp_server_to_gateway(
    client: MCPClientWrapper,
    gateway: ToolsGateway,
    category: Optional[str] = None,
) -> List[str]:
    """
    Connect to an MCP server, list its tools, convert to ToolDefinitions,
    and register them into the ToolsGateway.
    Returns list of successfully bridged tool IDs.
    """
    tools = await client.list_tools()
    bridged_ids = []

    for t in tools:
        tool_def = convert_mcp_tool_to_definition(t, client.config, category=category)
        handler = create_mcp_callable(client, t.name)
        
        # If tool already in registry, unregister first to update
        if gateway.registry.get_definition(t.name):
            gateway.registry.unregister(t.name)

        gateway.registry.register(tool_def, handler)
        bridged_ids.append(t.name)
        logger.info(
            f"Bridged MCP tool '{t.name}' into ToolsGateway "
            f"[tier={tool_def.permission_tier.value}, approval={tool_def.requires_approval}]"
        )

    return bridged_ids
