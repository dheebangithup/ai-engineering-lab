from typing import Any, Callable, Dict, List, Optional
from jarvis.tools.schemas import ToolDefinition


class ToolRegistryError(Exception):
    """Base exception for tool registry operations."""
    pass


class DuplicateToolError(ToolRegistryError):
    """Raised when registering a tool with an ID that already exists."""
    pass


class ToolNotFoundError(ToolRegistryError):
    """Raised when looking up an unregistered tool ID."""
    pass


class ToolRegistry:
    """
    In-memory registry managing tool definitions and their callable implementations.
    """

    def __init__(self) -> None:
        self._definitions: Dict[str, ToolDefinition] = {}
        self._implementations: Dict[str, Callable[..., Any]] = {}

    def register(
        self,
        tool_definition: ToolDefinition,
        implementation: Callable[..., Any],
    ) -> None:
        """
        Register a tool definition and its executable implementation.
        Raises DuplicateToolError if tool ID is already registered.
        """
        if tool_definition.id in self._definitions:
            raise DuplicateToolError(
                f"Tool with id '{tool_definition.id}' is already registered."
            )
        self._definitions[tool_definition.id] = tool_definition
        self._implementations[tool_definition.id] = implementation

    def get_definition(self, tool_id: str) -> ToolDefinition:
        """
        Retrieve tool definition by ID without exposing implementation.
        Raises ToolNotFoundError if not found.
        """
        if tool_id not in self._definitions:
            raise ToolNotFoundError(f"Tool '{tool_id}' not found in registry.")
        return self._definitions[tool_id]

    def get_implementation(self, tool_id: str) -> Callable[..., Any]:
        """
        Retrieve tool execution function by ID.
        Raises ToolNotFoundError if not found.
        """
        if tool_id not in self._implementations:
            raise ToolNotFoundError(f"Tool '{tool_id}' not found in registry.")
        return self._implementations[tool_id]

    def list_definitions(self) -> List[ToolDefinition]:
        """
        Return list of all registered tool definitions.
        """
        return list(self._definitions.values())

    def has_tool(self, tool_id: str) -> bool:
        """
        Check if tool ID exists in the registry.
        """
        return tool_id in self._definitions
