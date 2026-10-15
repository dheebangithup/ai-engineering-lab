from pathlib import Path
import pytest

from jarvis.tools.implementations import (
    CommandTools,
    FileSystemTools,
    register_default_tools,
)
from jarvis.tools.schemas import ToolDefinition, ToolResult
from jarvis.tools.tool_registry import ToolRegistry
from jarvis.tools.tools_gateway import ToolsGateway, validate_arguments, ValidationError


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    base = tmp_path / "sandbox"
    base.mkdir()
    # Create some initial files
    (base / "hello.txt").write_text("Hello World!", encoding="utf-8")
    sub = base / "sub"
    sub.mkdir()
    (sub / "nested.py").write_text("print('nested')", encoding="utf-8")
    return base


@pytest.fixture
def gateway(sandbox: Path) -> ToolsGateway:
    registry = ToolRegistry()
    register_default_tools(registry, allowed_base_dir=sandbox, allowed_commands={"echo", "ls", "date"})
    return ToolsGateway(registry)


def test_successful_list_files(gateway: ToolsGateway) -> None:
    result = gateway.execute("list_files", {"directory": "."})
    assert isinstance(result, ToolResult)
    assert result.success is True
    assert result.tool_id == "list_files"
    assert isinstance(result.data, list)
    paths = [item["path"] for item in result.data]
    assert "hello.txt" in paths
    assert "sub" in paths


def test_successful_read_file(gateway: ToolsGateway) -> None:
    result = gateway.execute("read_file", {"file_path": "hello.txt"})
    assert result.success is True
    assert result.data == "Hello World!"


def test_successful_write_file(gateway: ToolsGateway, sandbox: Path) -> None:
    result = gateway.execute(
        "write_file",
        {"file_path": "new_dir/output.txt", "content": "Created by gateway"},
    )
    assert result.success is True
    assert (sandbox / "new_dir" / "output.txt").read_text() == "Created by gateway"


def test_successful_search_files(gateway: ToolsGateway) -> None:
    result = gateway.execute("search_files", {"pattern": "Hello", "directory": "."})
    assert result.success is True
    assert len(result.data) >= 1
    assert result.data[0]["path"] == "hello.txt"
    assert "Hello World!" in result.data[0]["line_content"]


def test_successful_run_command(gateway: ToolsGateway) -> None:
    result = gateway.execute("run_command", {"command": "echo", "args": ["gateway", "test"]})
    assert result.success is True
    assert result.data["exit_code"] == 0
    assert "gateway test" in result.data["stdout"]


def test_unknown_tool_id(gateway: ToolsGateway) -> None:
    result = gateway.execute("non_existent_tool", {"foo": "bar"})
    assert isinstance(result, ToolResult)
    assert result.success is False
    assert "not found in registry" in result.error.lower()


def test_argument_validation_missing_required(gateway: ToolsGateway) -> None:
    # 'read_file' requires 'file_path'
    result = gateway.execute("read_file", {})
    assert result.success is False
    assert "missing required argument" in result.error.lower()
    assert "file_path" in result.error


def test_argument_validation_wrong_type(gateway: ToolsGateway) -> None:
    # 'file_path' must be string, pass integer
    result = gateway.execute("read_file", {"file_path": 12345})
    assert result.success is False
    assert "expected type 'string'" in result.error.lower()


def test_argument_validation_bool_for_int() -> None:
    schema = {
        "type": "object",
        "properties": {"count": {"type": "integer"}},
        "required": ["count"],
    }
    with pytest.raises(ValidationError):
        validate_arguments(schema, {"count": True})


def test_tool_implementation_failure_gracefully_handled() -> None:
    registry = ToolRegistry()
    def failing_tool() -> None:
        raise ValueError("Simulated internal algorithm failure")

    tool_def = ToolDefinition(
        id="failing_tool",
        name="Failing Tool",
        description="Fails intentionally.",
        parameters={"type": "object", "properties": {}, "required": []},
    )
    registry.register(tool_def, failing_tool)

    gw = ToolsGateway(registry)
    result = gw.execute("failing_tool", {})

    assert result.success is False
    assert "Execution error in 'failing_tool'" in result.error
    assert "Simulated internal algorithm failure" in result.error
    assert result.metadata.get("exception_type") == "ValueError"


def test_path_traversal_prevention(gateway: ToolsGateway) -> None:
    # Test relative path traversal
    result = gateway.execute("read_file", {"file_path": "../../outside.txt"})
    assert result.success is False
    assert "access denied" in result.error.lower()

    # Test writing outside allowed dir
    write_result = gateway.execute("write_file", {"file_path": "../escape.txt", "content": "malicious"})
    assert write_result.success is False
    assert "access denied" in write_result.error.lower()

    # Test absolute path outside allowed dir
    abs_result = gateway.execute("list_files", {"directory": "/etc"})
    assert abs_result.success is False
    assert "access denied" in abs_result.error.lower()


def test_command_allowlist_enforcement(gateway: ToolsGateway) -> None:
    # Try unpermitted command 'cat' or 'rm'
    result = gateway.execute("run_command", {"command": "rm", "args": ["-rf", "/tmp"]})
    assert result.success is False
    assert "not permitted" in result.error.lower()
