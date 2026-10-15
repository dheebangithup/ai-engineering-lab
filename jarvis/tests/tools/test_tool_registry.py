import pytest

from jarvis.tools.schemas import ToolDefinition
from jarvis.tools.tool_registry import (
    DuplicateToolError,
    ToolNotFoundError,
    ToolRegistry,
)


@pytest.fixture
def registry() -> ToolRegistry:
    return ToolRegistry()


@pytest.fixture
def sample_tool() -> ToolDefinition:
    return ToolDefinition(
        id="sample_tool",
        name="Sample Tool",
        description="A sample tool for testing.",
        parameters={
            "type": "object",
            "properties": {"arg1": {"type": "string"}},
            "required": ["arg1"],
        },
    )


def test_register_and_get_definition(registry: ToolRegistry, sample_tool: ToolDefinition) -> None:
    def dummy_impl(arg1: str) -> str:
        return arg1

    registry.register(sample_tool, dummy_impl)

    tool_def = registry.get_definition("sample_tool")
    assert tool_def.id == "sample_tool"
    assert tool_def.name == "Sample Tool"
    assert tool_def.description == "A sample tool for testing."
    assert "arg1" in tool_def.parameters["properties"]


def test_register_duplicate_tool_raises_error(registry: ToolRegistry, sample_tool: ToolDefinition) -> None:
    registry.register(sample_tool, lambda: None)

    with pytest.raises(DuplicateToolError) as exc_info:
        registry.register(sample_tool, lambda: None)

    assert "sample_tool" in str(exc_info.value)
    assert "already registered" in str(exc_info.value)


def test_get_unregistered_tool_definition_raises_error(registry: ToolRegistry) -> None:
    with pytest.raises(ToolNotFoundError) as exc_info:
        registry.get_definition("unknown_tool")

    assert "unknown_tool" in str(exc_info.value)


def test_get_unregistered_tool_implementation_raises_error(registry: ToolRegistry) -> None:
    with pytest.raises(ToolNotFoundError) as exc_info:
        registry.get_implementation("unknown_tool")

    assert "unknown_tool" in str(exc_info.value)


def test_has_tool(registry: ToolRegistry, sample_tool: ToolDefinition) -> None:
    assert not registry.has_tool("sample_tool")
    registry.register(sample_tool, lambda: None)
    assert registry.has_tool("sample_tool")


def test_list_definitions(registry: ToolRegistry, sample_tool: ToolDefinition) -> None:
    assert len(registry.list_definitions()) == 0

    tool2 = ToolDefinition(
        id="tool_two",
        name="Tool Two",
        description="Second tool.",
        parameters={},
    )

    registry.register(sample_tool, lambda: None)
    registry.register(tool2, lambda: None)

    defs = registry.list_definitions()
    assert len(defs) == 2
    ids = {d.id for d in defs}
    assert ids == {"sample_tool", "tool_two"}
