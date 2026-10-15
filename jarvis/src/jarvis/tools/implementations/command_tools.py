from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Set

from jarvis.tools.schemas import ToolDefinition


class CommandExecutionError(Exception):
    """Base exception for command tool failures."""
    pass


class CommandNotAllowedError(CommandExecutionError):
    """Raised when an attempt is made to execute a command outside the allowlist."""
    pass


DEFAULT_ALLOWED_COMMANDS: Set[str] = {
    "echo",
    "git",
    "python",
    "python3",
    "ls",
    "date",
    "whoami",
    "pwd",
}


class CommandTools:
    """
    Executes a strictly limited set of permitted commands without shell execution.
    """

    def __init__(
        self,
        allowed_commands: Optional[Set[str]] = None,
        timeout: int = 15,
        cwd: Optional[Path | str] = None,
    ) -> None:
        self.allowed_commands = allowed_commands if allowed_commands is not None else DEFAULT_ALLOWED_COMMANDS
        self.timeout = timeout
        self.cwd = Path(cwd).resolve() if cwd is not None else None

    def run_command(self, command: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Execute a permitted command with arguments.
        Does not invoke the system shell (shell=False) to prevent command injection.
        """
        command_clean = command.strip()
        if command_clean not in self.allowed_commands:
            raise CommandNotAllowedError(
                f"Command '{command_clean}' is not permitted. Allowed: {sorted(list(self.allowed_commands))}"
            )

        cmd_path = shutil.which(command_clean)
        if not cmd_path:
            raise FileNotFoundError(f"Command executable '{command_clean}' not found on system PATH.")

        cmd_list = [cmd_path] + (args if args is not None else [])

        try:
            completed = subprocess.run(
                cmd_list,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
                shell=False,
                cwd=str(self.cwd) if self.cwd else None,
            )
            return {
                "command": command_clean,
                "exit_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "success": completed.returncode == 0,
            }
        except subprocess.TimeoutExpired as e:
            raise CommandExecutionError(f"Command '{command_clean}' timed out after {self.timeout}s") from e
        except Exception as e:
            raise CommandExecutionError(f"Failed to execute command '{command_clean}': {str(e)}") from e


def create_command_tool_definition() -> ToolDefinition:
    """
    Create tool definition for run_command.
    """
    return ToolDefinition(
        id="run_command",
        name="Run Command",
        description="Execute a permitted system command safely without shell expansion.",
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Name of the command to execute (must be in allowlist).",
                },
                "args": {
                    "type": "array",
                    "description": "List of string arguments for the command.",
                },
            },
            "required": ["command"],
        },
    )
