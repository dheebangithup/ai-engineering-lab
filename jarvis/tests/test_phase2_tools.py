"""
Phase 2 Test Suite: Tools Gateway, Permission Interceptor, BM25 Tool Discovery,
Filesystem & Shell Tools, and the 3 Gateway Meta-Tools.
"""

from pathlib import Path
from unittest.mock import AsyncMock
import pytest

from jarvis.tools.implementations.filesystem import (
    PathTraversalError,
    list_files,
    read_file,
    search_files,
    write_file,
)
from jarvis.tools.implementations.shell import DisallowedCommandError, run_command
from jarvis.tools.meta_tools import create_gateway_meta_tools
from jarvis.tools.permissions import PermissionInterceptor
from jarvis.tools.schemas import PermissionRequest, PermissionTier, ToolResult
from jarvis.tools.tool_discovery import ToolDiscovery
from jarvis.tools.tool_gateway import ToolsGateway
from jarvis.tools.tool_registry import DuplicateToolError, ToolRegistry


@pytest.fixture
def populated_gateway() -> ToolsGateway:
    """Fixture returning a ToolsGateway initialized with built-in tools."""
    gateway = ToolsGateway()
    gateway.register_tool(list_files)
    gateway.register_tool(read_file)
    gateway.register_tool(write_file)
    gateway.register_tool(search_files)
    gateway.register_tool(run_command)
    return gateway


# =========================================================================
# 1. ToolRegistry Tests
# =========================================================================

def test_tool_registry_registration_and_deduplication():
    registry = ToolRegistry()
    registry.register(list_files._jarvis_tool_def, list_files)
    assert len(registry) == 1
    assert registry.get_definition("list_files") is not None

    with pytest.raises(DuplicateToolError):
        registry.register(list_files._jarvis_tool_def, list_files)


def test_tool_registry_categories(populated_gateway: ToolsGateway):
    categories = populated_gateway.registry.list_categories()
    assert "filesystem" in categories
    assert "shell" in categories

    fs_tools = populated_gateway.registry.list_tools(category="filesystem")
    assert any(t.tool_id == "read_file" for t in fs_tools)


# =========================================================================
# 2. ToolDiscovery BM25 Tests
# =========================================================================

def test_tool_discovery_natural_language(populated_gateway: ToolsGateway):
    discovery = populated_gateway.discovery

    # Query for file reading
    results = discovery.search("I want to inspect and read a file's content")
    assert len(results) > 0
    assert results[0].tool_id == "read_file"

    # Query for command execution
    shell_results = discovery.search("execute terminal command or bash process")
    assert len(shell_results) > 0
    assert shell_results[0].tool_id == "run_command"


# =========================================================================
# 3. Permission Interceptor Tests (Human-in-the-Loop)
# =========================================================================

@pytest.mark.anyio
async def test_permission_interceptor_safe_auto_allows(populated_gateway: ToolsGateway):
    # list_files is SAFE -> no approval callback required
    result = await populated_gateway.execute_tool("list_files", {"directory": "."})
    assert result.success is True
    assert result.permission_denied is False


@pytest.mark.anyio
async def test_permission_interceptor_dangerous_denied_without_callback(populated_gateway: ToolsGateway):
    # run_command is DANGEROUS -> without callback, it must be denied
    result = await populated_gateway.execute_tool(
        "run_command", {"command": "ls", "args": []}
    )
    assert result.success is False
    assert result.permission_denied is True
    assert "Permission denied" in result.error


@pytest.mark.anyio
async def test_permission_interceptor_with_user_approval_callback():
    # Setup approval handler that grants permission
    async def mock_approval(req: PermissionRequest) -> bool:
        assert req.tool_id == "run_command"
        assert req.permission_tier == PermissionTier.DANGEROUS
        return True

    interceptor = PermissionInterceptor(approval_callback=mock_approval)
    gateway = ToolsGateway(permission_interceptor=interceptor)
    gateway.register_tool(run_command)

    result = await gateway.execute_tool("run_command", {"command": "echo", "args": ["hello_jarvis"]})
    assert result.success is True
    assert result.data["exit_code"] == 0
    assert "hello_jarvis" in result.data["stdout"]


@pytest.mark.anyio
async def test_permission_interceptor_user_rejects_dangerous_action():
    # Setup approval handler that rejects permission
    async def mock_approval(req: PermissionRequest) -> bool:
        return False  # User clicked "Deny"

    interceptor = PermissionInterceptor(approval_callback=mock_approval)
    gateway = ToolsGateway(permission_interceptor=interceptor)
    gateway.register_tool(run_command)

    result = await gateway.execute_tool("run_command", {"command": "echo", "args": ["danger"]})
    assert result.success is False
    assert result.permission_denied is True


# =========================================================================
# 4. Filesystem & Shell Security Safeguards Tests
# =========================================================================

@pytest.mark.anyio
async def test_filesystem_path_traversal_blocked(populated_gateway: ToolsGateway):
    with pytest.raises(PathTraversalError):
        await read_file(path="../../../../etc/passwd")


@pytest.mark.anyio
async def test_shell_disallowed_command_blocked(populated_gateway: ToolsGateway):
    with pytest.raises(DisallowedCommandError):
        await run_command(command="rm", args=["-rf", "/"])


# =========================================================================
# 5. The 3 Meta-Tools (Uber Architecture) Tests
# =========================================================================

@pytest.mark.anyio
async def test_meta_tools_workflow(populated_gateway: ToolsGateway):
    search_tools_fn, list_tools_fn, execute_tool_fn = create_gateway_meta_tools(populated_gateway)

    # 1. Agent searches for tools
    discovered = await search_tools_fn(query="search text in files")
    assert len(discovered) > 0
    assert any(t["tool_id"] == "search_files" for t in discovered)

    # 2. Agent lists tools
    categories = await list_tools_fn()
    assert "filesystem" in categories["available_categories"]

    # 3. Agent executes a tool via execute_tool
    res = await execute_tool_fn(tool_id="list_files", arguments={"directory": "."})
    assert res["success"] is True
    assert "items" in res["data"]
