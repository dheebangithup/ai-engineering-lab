"""
Permission and Security Interceptor for the J.A.R.V.I.S. Tools Gateway.
Enforces human-in-the-loop authorization for sensitive and dangerous actions.
"""

from typing import Any, Awaitable, Callable, Dict, Optional
from jarvis.logger import get_logger
from jarvis.tools.schemas import PermissionRequest, PermissionTier, ToolDefinition, ToolResult

logger = get_logger("tools.permissions")

# Signature for an async approval callback: (PermissionRequest) -> bool
ApprovalCallback = Callable[[PermissionRequest], Awaitable[bool]]


class PermissionInterceptor:
    """
    Evaluates whether a tool execution requires human authorization,
    and invokes the configured approval handler.
    """

    def __init__(
        self,
        approval_callback: Optional[ApprovalCallback] = None,
        auto_approve_sensitive: bool = True,
        auto_approve_dangerous: bool = False,
    ):
        self.approval_callback = approval_callback
        self.auto_approve_sensitive = auto_approve_sensitive
        self.auto_approve_dangerous = auto_approve_dangerous

    async def verify_permission(
        self,
        tool: ToolDefinition,
        arguments: Dict[str, Any],
    ) -> bool:
        """
        Check whether tool execution is permitted.
        Returns True if authorized, False if denied.
        """
        # SAFE tools are always authorized
        if tool.permission_tier == PermissionTier.SAFE and not tool.requires_approval:
            return True

        # SENSITIVE tools: check policy
        if tool.permission_tier == PermissionTier.SENSITIVE and not tool.requires_approval:
            if self.auto_approve_sensitive:
                logger.info(f"Auto-approved sensitive tool '{tool.tool_id}'")
                return True

        # DANGEROUS tools (or explicitly flagged): require approval callback
        if tool.permission_tier == PermissionTier.DANGEROUS or tool.requires_approval:
            if self.auto_approve_dangerous:
                logger.warning(f"DANGEROUS tool '{tool.tool_id}' auto-approved by override policy!")
                return True

            if self.approval_callback is None:
                logger.warning(
                    f"Execution of dangerous tool '{tool.tool_id}' blocked: No approval callback registered"
                )
                return False

            request = PermissionRequest(
                tool_id=tool.tool_id,
                tool_name=tool.name,
                permission_tier=tool.permission_tier,
                arguments=arguments,
                reason=f"Action classified as {tool.permission_tier.value.upper()}",
            )

            logger.info(f"Requesting human permission for tool '{tool.tool_id}'...")
            approved = await self.approval_callback(request)
            if approved:
                logger.info(f"Permission GRANTED for tool '{tool.tool_id}'")
                return True
            else:
                logger.warning(f"Permission DENIED by user for tool '{tool.tool_id}'")
                return False

        return True
