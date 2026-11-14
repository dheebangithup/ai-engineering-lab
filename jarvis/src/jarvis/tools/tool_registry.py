"""
Tool Registry for J.A.R.V.I.S.
Maintains in-memory tool definitions, category indexes, and execution handlers.
"""

from typing import Any, Callable, Dict, List, Optional
from jarvis.logger import get_logger
from jarvis.tools.schemas import ToolDefinition

logger = get_logger("tools.registry")


class DuplicateToolError(ValueError):
    """Raised when attempting to register a tool with an already existing tool_id."""
    pass


class ToolNotFoundError(KeyError):
    """Raised when a requested tool_id is not found in the registry."""
    pass


class ToolRegistry:
    """Central store for all available tools in J.A.R.V.I.S."""

    def __init__(self):
        self._definitions: Dict[str, ToolDefinition] = {}
        self._handlers: Dict[str, Callable] = {}
        self._category_index: Dict[str, List[str]] = {}

    def register(self, definition: ToolDefinition, handler: Callable) -> None:
        """Register a new tool and its execution callable."""
        if definition.tool_id in self._definitions:
            raise DuplicateToolError(f"Tool with ID '{definition.tool_id}' is already registered")

        self._definitions[definition.tool_id] = definition
        self._handlers[definition.tool_id] = handler

        cat = definition.category.lower()
        if cat not in self._category_index:
            self._category_index[cat] = []
        self._category_index[cat].append(definition.tool_id)

        logger.debug(f"Registered tool: {definition.tool_id} (category: {definition.category}, tier: {definition.permission_tier.value})")

    def unregister(self, tool_id: str) -> bool:
        """Unregister a tool by ID."""
        if tool_id not in self._definitions:
            return False

        definition = self._definitions.pop(tool_id)
        self._handlers.pop(tool_id, None)

        cat = definition.category.lower()
        if cat in self._category_index and tool_id in self._category_index[cat]:
            self._category_index[cat].remove(tool_id)

        return True

    def get_definition(self, tool_id: str) -> Optional[ToolDefinition]:
        """Retrieve public ToolDefinition metadata."""
        return self._definitions.get(tool_id)

    def get_handler(self, tool_id: str) -> Optional[Callable]:
        """Retrieve private callable implementation."""
        return self._handlers.get(tool_id)

    def list_tools(self, category: Optional[str] = None) -> List[ToolDefinition]:
        """List all tool definitions, optionally filtered by category."""
        if category:
            tool_ids = self._category_index.get(category.lower(), [])
            return [self._definitions[tid] for tid in tool_ids if tid in self._definitions]
        return list(self._definitions.values())

    def list_categories(self) -> List[str]:
        """List all distinct tool categories."""
        return sorted(list(self._category_index.keys()))

    def __len__(self) -> int:
        return len(self._definitions)
