"""
Shell command execution tool for J.A.R.V.I.S.
Classified as DANGEROUS with mandatory permission verification and strict allowlists.
"""

import asyncio
from typing import Any, Dict, List, Optional
from jarvis.tools.decorators import jarvis_tool
from jarvis.tools.schemas import PermissionTier, ToolParameter

ALLOWED_COMMANDS = {
    "git", "pytest", "python", "uv", "ls", "echo", "pwd",
    "cat", "grep", "find", "head", "tail", "wc", "stat",
}


class DisallowedCommandError(PermissionError):
    """Raised when an unapproved executable binary is invoked."""
    pass


@jarvis_tool(
    tool_id="run_command",
    name="Run System Command",
    description="Execute an approved CLI command within the workspace. Requires explicit user permission.",
    category="shell",
    permission_tier=PermissionTier.DANGEROUS,
    requires_approval=True,
    parameters={
        "command": ToolParameter(
            type="string",
            description="Command executable to run (must be on allowlist)",
            required=True,
            enum=sorted(list(ALLOWED_COMMANDS)),
        ),
        "args": ToolParameter(
            type="array",
            description="List of arguments for the command",
            default=[],
        ),
        "timeout_seconds": ToolParameter(
            type="integer",
            description="Maximum execution timeout in seconds",
            default=30,
        ),
    },
)
async def run_command(
    command: str,
    args: Optional[List[str]] = None,
    timeout_seconds: int = 30,
) -> Dict[str, Any]:
    cmd_name = command.strip().lower()
    if cmd_name not in ALLOWED_COMMANDS:
        raise DisallowedCommandError(
            f"Command '{command}' is not in the approved allowlist: {sorted(list(ALLOWED_COMMANDS))}"
        )

    arg_list = args or []
    # Execute securely with shell=False
    proc = await asyncio.create_subprocess_exec(
        cmd_name,
        *arg_list,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(),
            timeout=float(timeout_seconds),
        )
        return {
            "command": cmd_name,
            "args": arg_list,
            "exit_code": proc.returncode,
            "stdout": stdout_bytes.decode("utf-8", errors="replace"),
            "stderr": stderr_bytes.decode("utf-8", errors="replace"),
            "success": proc.returncode == 0,
        }
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        raise TimeoutError(f"Command '{cmd_name}' timed out after {timeout_seconds} seconds")
