import traceback
from typing import Any, Dict, List, Optional

from jarvis.logger import get_logger
from jarvis.tools.schemas import ToolDefinition, ToolResult
from jarvis.tools.tool_registry import ToolNotFoundError, ToolRegistry

logger = get_logger("tools.gateway")


class ValidationError(Exception):
    """Raised when tool arguments fail schema validation."""
    pass


def validate_arguments(parameters_schema: Dict[str, Any], arguments: Dict[str, Any]) -> None:
    """
    Validate an arguments dictionary against a JSON Schema compatible parameter specification.
    Checks:
    - Root object type
    - Required fields
    - Basic property types (string, integer, number, boolean, array, object)
    """
    if not isinstance(arguments, dict):
        raise ValidationError(f"Arguments must be a dictionary, got {type(arguments).__name__}")

    required_fields: List[str] = parameters_schema.get("required", [])
    for field_name in required_fields:
        if field_name not in arguments:
            raise ValidationError(f"Missing required argument: '{field_name}'")

    properties: Dict[str, Any] = parameters_schema.get("properties", {})
    type_mapping = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": (list, tuple),
        "object": dict,
    }

    for arg_name, arg_val in arguments.items():
        if arg_name not in properties:
            # We allow extra arguments if additionalProperties is not explicitly False
            if parameters_schema.get("additionalProperties") is False:
                raise ValidationError(f"Unexpected argument: '{arg_name}'")
            continue

        prop_spec = properties[arg_name]
        expected_type_str = prop_spec.get("type")
        if not expected_type_str:
            continue

        expected_type = type_mapping.get(expected_type_str)
        if expected_type is None:
            continue

        # In Python, bool is a subclass of int, so handle carefully
        if expected_type_str == "boolean":
            if not isinstance(arg_val, bool):
                raise ValidationError(
                    f"Argument '{arg_name}' expected type 'boolean', got '{type(arg_val).__name__}'"
                )
        elif expected_type_str in ("integer", "number"):
            if isinstance(arg_val, bool) or not isinstance(arg_val, expected_type):
                raise ValidationError(
                    f"Argument '{arg_name}' expected type '{expected_type_str}', got '{type(arg_val).__name__}'"
                )
        else:
            if not isinstance(arg_val, expected_type):
                raise ValidationError(
                    f"Argument '{arg_name}' expected type '{expected_type_str}', got '{type(arg_val).__name__}'"
                )


class ToolsGateway:
    """
    Central execution gateway for all registered tools.
    Handles resolution, validation, execution, and standardized error handling.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def execute(self, tool_id: str, arguments: Optional[Dict[str, Any]] = None) -> ToolResult:
        """
        Execute a tool by ID with arguments.
        Always returns a structured ToolResult.
        """
        if arguments is None:
            arguments = {}

        logger.info(f"Gateway executing tool: '{tool_id}' with args: {arguments}")

        # 1. Resolve tool definition and implementation
        try:
            tool_def = self._registry.get_definition(tool_id)
            implementation = self._registry.get_implementation(tool_id)
        except ToolNotFoundError as e:
            logger.error(f"Tool '{tool_id}' resolution error: {e}")
            return ToolResult(
                tool_id=tool_id,
                success=False,
                error=f"Tool resolution error: {str(e)}",
            )

        # 2. Validate arguments against schema
        try:
            validate_arguments(tool_def.parameters, arguments)
        except ValidationError as e:
            logger.warning(f"Tool '{tool_id}' validation error: {e}")
            return ToolResult(
                tool_id=tool_id,
                success=False,
                error=f"Argument validation failed: {str(e)}",
            )

        # 3. Execute implementation
        try:
            raw_result = implementation(**arguments)

            if isinstance(raw_result, ToolResult):
                logger.info(f"Tool '{tool_id}' completed: success={raw_result.success}")
                return raw_result

            logger.info(f"Tool '{tool_id}' completed successfully")
            return ToolResult(
                tool_id=tool_id,
                success=True,
                data=raw_result,
            )
        except Exception as e:
            logger.error(f"Tool '{tool_id}' raised exception: {e}", exc_info=True)
            return ToolResult(
                tool_id=tool_id,
                success=False,
                error=f"Execution error in '{tool_id}': {str(e)}",
                metadata={"exception_type": type(e).__name__},
            )
