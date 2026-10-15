from pathlib import Path
from typing import Any, Dict, List, Optional

from jarvis.tools.schemas import ToolDefinition


class PathTraversalError(PermissionError):
    """Raised when an operation targets a path outside the allowed base directory."""
    pass


class FileSystemTools:
    """
    Filesystem tools constrained to a strictly enforced allowed base directory.
    Prevents path traversal and unrestricted file access.
    """

    def __init__(self, allowed_base_dir: Path | str) -> None:
        self.base_dir = Path(allowed_base_dir).resolve()

    def _resolve_safe_path(self, relative_or_absolute_path: str) -> Path:
        """
        Resolve path against the allowed base directory and verify it does not escape.
        """
        target = Path(relative_or_absolute_path)
        if not target.is_absolute():
            resolved = (self.base_dir / target).resolve()
        else:
            resolved = target.resolve()

        try:
            resolved.relative_to(self.base_dir)
        except ValueError:
            raise PathTraversalError(
                f"Access denied: '{relative_or_absolute_path}' is outside the allowed directory '{self.base_dir}'"
            )
        return resolved

    def list_files(self, directory: str = ".", recursive: bool = False) -> List[Dict[str, Any]]:
        """
        List files in an allowed directory.
        """
        target_dir = self._resolve_safe_path(directory)
        if not target_dir.exists():
            raise FileNotFoundError(f"Directory not found: '{directory}'")
        if not target_dir.is_dir():
            raise NotADirectoryError(f"Path is not a directory: '{directory}'")

        entries: List[Dict[str, Any]] = []
        iterator = target_dir.rglob("*") if recursive else target_dir.iterdir()

        for path in iterator:
            try:
                rel_path = path.relative_to(self.base_dir)
                entries.append({
                    "name": path.name,
                    "path": str(rel_path),
                    "is_dir": path.is_dir(),
                    "size": path.stat().st_size if path.is_file() else 0,
                })
            except Exception:
                continue

        entries.sort(key=lambda x: (not x["is_dir"], x["path"]))
        return entries

    def read_file(self, file_path: str) -> str:
        """
        Read text content of a file from the allowed directory.
        """
        safe_path = self._resolve_safe_path(file_path)
        if not safe_path.exists():
            raise FileNotFoundError(f"File not found: '{file_path}'")
        if not safe_path.is_file():
            raise IsADirectoryError(f"Path is a directory, not a file: '{file_path}'")

        return safe_path.read_text(encoding="utf-8")

    def write_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Write text content to a file in the allowed directory.
        Creates parent directories if necessary.
        """
        safe_path = self._resolve_safe_path(file_path)
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        safe_path.write_text(content, encoding="utf-8")
        return {
            "path": str(safe_path.relative_to(self.base_dir)),
            "bytes_written": len(content.encode("utf-8")),
            "status": "success",
        }

    def search_files(self, pattern: str, directory: str = ".") -> List[Dict[str, Any]]:
        """
        Search files in the allowed directory for a text pattern.
        """
        target_dir = self._resolve_safe_path(directory)
        if not target_dir.exists():
            raise FileNotFoundError(f"Directory not found: '{directory}'")
        if not target_dir.is_dir():
            raise NotADirectoryError(f"Path is not a directory: '{directory}'")

        matches: List[Dict[str, Any]] = []
        for file_path in target_dir.rglob("*"):
            if not file_path.is_file():
                continue
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for line_num, line in enumerate(content.splitlines(), start=1):
                    if pattern in line:
                        rel_path = file_path.relative_to(self.base_dir)
                        matches.append({
                            "path": str(rel_path),
                            "line_number": line_num,
                            "line_content": line.strip(),
                        })
            except Exception:
                continue

        return matches


def create_filesystem_tool_definitions() -> Dict[str, ToolDefinition]:
    """
    Create tool definitions for the filesystem tools.
    """
    return {
        "list_files": ToolDefinition(
            id="list_files",
            name="List Files",
            description="List files and directories within an allowed workspace directory.",
            parameters={
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Relative path to directory to list. Defaults to '.'",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Whether to list files recursively.",
                    },
                },
                "required": [],
            },
        ),
        "read_file": ToolDefinition(
            id="read_file",
            name="Read File",
            description="Read the complete text content of a specified file.",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Relative path of the file to read.",
                    },
                },
                "required": ["file_path"],
            },
        ),
        "write_file": ToolDefinition(
            id="write_file",
            name="Write File",
            description="Write text content to a file in the allowed workspace directory.",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Relative path of the file to write.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Text content to write into the file.",
                    },
                },
                "required": ["file_path", "content"],
            },
        ),
        "search_files": ToolDefinition(
            id="search_files",
            name="Search Files",
            description="Search files in the allowed workspace directory for a specific text pattern or keyword.",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Text string or pattern to search for.",
                    },
                    "directory": {
                        "type": "string",
                        "description": "Relative path to start searching from. Defaults to '.'",
                    },
                },
                "required": ["pattern"],
            },
        ),
    }
