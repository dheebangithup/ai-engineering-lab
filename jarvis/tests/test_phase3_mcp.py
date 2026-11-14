"""
Phase 3 Test Suite: MCP Multi-Server Engine & Strata Memory Integration.
Tests tool conversion, permission tiers (delete, purge, prune, edit require permission),
and integration into the Tools Gateway and 3 Meta-Tools.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest
import mcp.types as types

from jarvis.mcp.bridge import (
    bridge_mcp_server_to_gateway,
    convert_mcp_tool_to_definition,
    determine_permission_tier,
)
from jarvis.mcp.mcp_client import MCPClientWrapper
from jarvis.mcp.mcp_manager import MCPManager
from jarvis.mcp.mcp_store import MCPStore
from jarvis.mcp.schemas import MCPServerConfig, MCPTransportType
from jarvis.tools.meta_tools import create_gateway_meta_tools
from jarvis.tools.permissions import PermissionInterceptor
from jarvis.tools.schemas import PermissionRequest, PermissionTier
from jarvis.tools.tool_gateway import ToolsGateway


@pytest.fixture
def temp_mcp_store(tmp_path: Path) -> MCPStore:
    """Isolated MCP store for testing."""
    settings_file = tmp_path / "settings" / "mcp_servers.json"
    return MCPStore(settings_file=settings_file)


# =========================================================================
# 1. Permission Tier & Security Rules Tests
# =========================================================================

def test_mcp_security_rules_for_strata_memory():
    """Verify that delete, purge, prune, and edit ALWAYS require permission."""
    config = MCPServerConfig(
        server_id="strata-memory",
        name="Strata Memory",
        command="strata-mcp",
    )

    # 1. Dangerous actions (ALWAYS PERMISSION NEEDED)
    dangerous_tools = [
        "memory_delete",
        "memory_prune",
        "memory_purge_namespace",
        "memory_edit",
    ]
    for tool_name in dangerous_tools:
        tier, requires_approval = determine_permission_tier(tool_name, config)
        assert tier == PermissionTier.DANGEROUS, f"{tool_name} must be DANGEROUS"
        assert requires_approval is True, f"{tool_name} must require human approval"

    # 2. Sensitive actions
    sensitive_tools = ["memory_ingest", "memory_store_explicit"]
    for tool_name in sensitive_tools:
        tier, requires_approval = determine_permission_tier(tool_name, config)
        assert tier == PermissionTier.SENSITIVE, f"{tool_name} must be SENSITIVE"

    # 3. Safe actions
    safe_tools = ["memory_recall", "memory_feedback"]
    for tool_name in safe_tools:
        tier, requires_approval = determine_permission_tier(tool_name, config)
        assert tier == PermissionTier.SAFE, f"{tool_name} must be SAFE"
        assert requires_approval is False, f"{tool_name} should not require approval"


# =========================================================================
# 2. MCPStore Configuration & UI Readiness Tests
# =========================================================================

def test_mcp_store_seed_and_management(temp_mcp_store: MCPStore):
    """Test seed creation and runtime addition/removal of servers (UI ready)."""
    cfg = temp_mcp_store.load_config()
    assert "strata-memory" in cfg.servers
    strata = cfg.servers["strata-memory"]
    assert strata.transport == MCPTransportType.STDIO

    # Add new server (e.g. from UI)
    github_server = MCPServerConfig(
        server_id="github-mcp",
        name="GitHub Tools",
        transport=MCPTransportType.STDIO,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
    )
    temp_mcp_store.add_or_update_server(github_server)

    reloaded = temp_mcp_store.load_config()
    assert "github-mcp" in reloaded.servers
    assert reloaded.servers["github-mcp"].command == "npx"

    # Remove server
    assert temp_mcp_store.remove_server("github-mcp") is True
    assert "github-mcp" not in temp_mcp_store.load_config().servers


# =========================================================================
# 3. Tool Conversion & Bridge Tests
# =========================================================================

def test_convert_mcp_tool_to_definition():
    server_cfg = MCPServerConfig(server_id="strata-memory", name="Strata")
    mcp_tool = types.Tool(
        name="memory_recall",
        description="Search memories across pillars",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "top_k": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    )

    definition = convert_mcp_tool_to_definition(mcp_tool, server_cfg)
    assert definition.tool_id == "memory_recall"
    assert definition.category == "memory"
    assert definition.permission_tier == PermissionTier.SAFE
    assert definition.requires_approval is False
    assert "query" in definition.parameters
    assert definition.parameters["query"].required is True


# =========================================================================
# 4. End-to-End MCP Gateway Bridging & Permission Enforcement Tests
# =========================================================================

@pytest.mark.anyio
async def test_mcp_bridge_and_permission_enforcement():
    """Verify that bridged MCP tools enforce permissions and are discovered by BM25."""
    # Mock MCP Client with strata memory tools
    mock_client = AsyncMock(spec=MCPClientWrapper)
    mock_client.config = MCPServerConfig(server_id="strata-memory", name="Strata Memory")
    mock_client.list_tools.return_value = [
        types.Tool(
            name="memory_recall",
            description="Recall and search past conversations and facts",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        ),
        types.Tool(
            name="memory_delete",
            description="Delete specific memory by ID",
            input_schema={"type": "object", "properties": {"target_id": {"type": "string"}}, "required": ["target_id"]},
        ),
    ]
    mock_client.call_tool.return_value = {"output": "Memory deleted successfully", "is_error": False}

    gateway = ToolsGateway()
    bridged_ids = await bridge_mcp_server_to_gateway(mock_client, gateway)
    assert "memory_recall" in bridged_ids
    assert "memory_delete" in bridged_ids

    # 1. Natural Language Discovery via BM25
    found = gateway.discover_tools("search for user memories and past projects")
    assert len(found) > 0
    assert found[0].tool_id == "memory_recall"

    # 2. Execution of memory_recall (SAFE -> succeeds without approval)
    mock_client.call_tool.return_value = {"output": "Recalled facts...", "is_error": False}
    recall_res = await gateway.execute_tool("memory_recall", {"query": "test query"})
    assert recall_res.success is True

    # 3. Execution of memory_delete WITHOUT approval callback -> BLOCKED
    del_blocked = await gateway.execute_tool("memory_delete", {"target_id": "uuid-123"})
    assert del_blocked.success is False
    assert del_blocked.permission_denied is True
    assert "Permission denied" in del_blocked.error

    # 4. Execution of memory_delete WITH human approval callback -> GRANTED
    mock_client.call_tool.return_value = {"output": "Memory deleted successfully", "is_error": False}
    async def user_approves(req: PermissionRequest) -> bool:
        assert req.tool_id == "memory_delete"
        assert req.permission_tier == PermissionTier.DANGEROUS
        return True

    gateway.permissions.approval_callback = user_approves
    del_approved = await gateway.execute_tool("memory_delete", {"target_id": "uuid-123"})
    assert del_approved.success is True
    assert del_approved.data["output"] == "Memory deleted successfully"


# =========================================================================
# 5. MCP Tools Exposed via 3 Meta-Tools (The Uber Pattern)
# =========================================================================

@pytest.mark.anyio
async def test_mcp_meta_tools_integration():
    """Verify that agents interact with MCP memory tools strictly through the 3 Meta-Tools."""
    mock_client = AsyncMock(spec=MCPClientWrapper)
    mock_client.config = MCPServerConfig(server_id="strata-memory", name="Strata")
    mock_client.list_tools.return_value = [
        types.Tool(
            name="memory_recall",
            description="Recall facts and past context",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        ),
    ]
    mock_client.call_tool.return_value = {"output": "<strata_memory_context>User prefers Python</strata_memory_context>"}

    gateway = ToolsGateway()
    await bridge_mcp_server_to_gateway(mock_client, gateway)

    search_fn, list_fn, exec_fn = create_gateway_meta_tools(gateway)

    # 1. Agent searches for memory
    tools = await search_fn(query="recall context")
    assert len(tools) > 0
    assert tools[0]["tool_id"] == "memory_recall"

    # 2. Agent executes memory_recall via execute_tool
    res = await exec_fn(tool_id="memory_recall", arguments={"query": "user preferences"})
    assert res["success"] is True
    assert "User prefers Python" in res["data"]["output"]
