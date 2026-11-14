"""
Decorators for J.A.R.V.I.S. tool registration.
"""

from functools import wraps
import inspect
from typing import Any, Callable, Dict, Optional
from jarvis.tools.schemas import PermissionTier, ToolDefinition, ToolParameter


def jarvis_tool(
    tool_id: str,
    name: str,
    description: str,
    category: str = "general",
    permission_tier: PermissionTier = PermissionTier.SAFE,
    requires_approval: bool = False,
    parameters: Optional[Dict[str, ToolParameter]] = None,
):
    """
    Decorator to mark a function as a J.A.R.V.I.S. tool.
    Attaches the ToolDefinition metadata to the function.
    """
    def decorator(fn: Callable):
        # Auto-infer parameters from type hints if not explicitly provided
        params = parameters or {}
        if not params:
            sig = inspect.signature(fn)
            for p_name, param in sig.parameters.items():
                if p_name in ("self", "cls"):
                    continue
                type_name = "string"
                if param.annotation == int:
                    type_name = "integer"
                elif param.annotation == float:
                    type_name = "number"
                elif param.annotation == bool:
                    type_name = "boolean"
                elif param.annotation in (list, List):
                    type_name = "array"
                elif param.annotation in (dict, Dict):
                    type_name = "object"

                is_required = param.default == inspect.Parameter.empty
                default_val = None if is_required else param.default

                params[p_name] = ToolParameter(
                    type=type_name,
                    description=f"Parameter {p_name}",
                    required=is_required,
                    default=default_val,
                )

        definition = ToolDefinition(
            tool_id=tool_id,
            name=name,
            description=description,
            category=category,
            permission_tier=permission_tier,
            requires_approval=requires_approval,
            parameters=params,
        )

        fn._jarvis_tool_def = definition  # type: ignore

        @wraps(fn)
        async def async_wrapper(*args, **kwargs):
            if inspect.iscoroutinefunction(fn):
                return await fn(*args, **kwargs)
            return fn(*args, **kwargs)

        async_wrapper._jarvis_tool_def = definition  # type: ignore
        return async_wrapper

    return decorator
