from pathlib import Path
from typing import Optional, Set

from jarvis.tools.implementations.command_tools import (
    CommandExecutionError,
    CommandNotAllowedError,
    CommandTools,
    DEFAULT_ALLOWED_COMMANDS,
    create_command_tool_definition,
)
from jarvis.tools.implementations.filesystem_tools import (
    FileSystemTools,
    PathTraversalError,
    create_filesystem_tool_definitions,
)
from jarvis.tools.tool_registry import ToolRegistry


def register_default_tools(
    registry: ToolRegistry,
    allowed_base_dir: Path | str,
    allowed_commands: Optional[Set[str]] = None,
) -> None:
    """
    Convenience function to register all five initial default tools:
    - list_files
    - read_file
    - write_file
    - search_files
    - run_command
    """
    fs = FileSystemTools(allowed_base_dir=allowed_base_dir)
    fs_defs = create_filesystem_tool_definitions()

    registry.register(fs_defs["list_files"], fs.list_files)
    registry.register(fs_defs["read_file"], fs.read_file)
    registry.register(fs_defs["write_file"], fs.write_file)
    registry.register(fs_defs["search_files"], fs.search_files)

    cmd = CommandTools(allowed_commands=allowed_commands, cwd=allowed_base_dir)
    cmd_def = create_command_tool_definition()
    registry.register(cmd_def, cmd.run_command)


__all__ = [
    "FileSystemTools",
    "PathTraversalError",
    "create_filesystem_tool_definitions",
    "CommandTools",
    "CommandNotAllowedError",
    "CommandExecutionError",
    "create_command_tool_definition",
    "DEFAULT_ALLOWED_COMMANDS",
    "register_default_tools",
]
