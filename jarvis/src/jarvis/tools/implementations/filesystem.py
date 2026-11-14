"""
Filesystem tool implementations for J.A.R.V.I.S.
Includes path traversal protections and permission tier definitions.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from jarvis.tools.decorators import jarvis_tool
from jarvis.tools.schemas import PermissionTier, ToolParameter
from jarvis.workspace import default_workspace


class PathTraversalError(PermissionError):
    """Raised when an attempt is made to escape allowed directory boundaries."""
    pass


def _resolve_safe_path(target_path: str | Path, base_dir: Optional[Path] = None) -> Path:
    """Ensure path resolves cleanly without escaping the permitted root."""
    base = (base_dir or Path.cwd()).resolve()
    target = (base / target_path).resolve() if not Path(target_path).is_absolute() else Path(target_path).resolve()

    # Allow current working directory or default workspace root
    ws_root = default_workspace().root_dir.resolve()
    cwd_root = Path.cwd().resolve()

    # Path must be inside either workspace root or current project working directory
    is_under_ws = ws_root in target.parents or target == ws_root
    is_under_cwd = cwd_root in target.parents or target == cwd_root

    if not (is_under_ws or is_under_cwd):
        raise PathTraversalError(f"Access denied: Path '{target}' is outside allowed workspace boundaries.")

    return target


@jarvis_tool(
    tool_id="list_files",
    name="List Files",
    description="List files and directories within a specified path.",
    category="filesystem",
    permission_tier=PermissionTier.SAFE,
    parameters={
        "directory": ToolParameter(type="string", description="Relative or absolute directory path to list", default="."),
        "recursive": ToolParameter(type="boolean", description="Whether to recurse into subdirectories", default=False),
    },
)
async def list_files(directory: str = ".", recursive: bool = False) -> Dict[str, Any]:
    safe_dir = _resolve_safe_path(directory)
    if not safe_dir.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    if not safe_dir.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {directory}")

    items = []
    if recursive:
        for p in safe_dir.rglob("*"):
            if not any(part.startswith(".") for part in p.parts):
                items.append({
                    "name": p.name,
                    "path": str(p.relative_to(safe_dir)),
                    "is_dir": p.is_dir(),
                    "size": p.stat().st_size if p.is_file() else None,
                })
    else:
        for p in safe_dir.iterdir():
            if not p.name.startswith("."):
                items.append({
                    "name": p.name,
                    "path": str(p.relative_to(safe_dir)),
                    "is_dir": p.is_dir(),
                    "size": p.stat().st_size if p.is_file() else None,
                })

    return {"directory": str(safe_dir), "items": items, "count": len(items)}


@jarvis_tool(
    tool_id="read_file",
    name="Read File",
    description="Read the textual contents of a file within the workspace.",
    category="filesystem",
    permission_tier=PermissionTier.SAFE,
    parameters={
        "path": ToolParameter(type="string", description="File path to read", required=True),
        "max_bytes": ToolParameter(type="integer", description="Maximum bytes to read", default=50000),
    },
)
async def read_file(path: str, max_bytes: int = 50000) -> Dict[str, Any]:
    safe_path = _resolve_safe_path(path)
    if not safe_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not safe_path.is_file():
        raise IsADirectoryError(f"Path is a directory, not a file: {path}")

    content = safe_path.read_text(encoding="utf-8", errors="replace")[:max_bytes]
    return {
        "path": str(safe_path),
        "size_bytes": safe_path.stat().st_size,
        "content": content,
        "truncated": safe_path.stat().st_size > max_bytes,
    }


@jarvis_tool(
    tool_id="write_file",
    name="Write File",
    description="Write text content to a file inside the workspace. Overwrites or creates the file.",
    category="filesystem",
    permission_tier=PermissionTier.SENSITIVE,
    parameters={
        "path": ToolParameter(type="string", description="File path to write", required=True),
        "content": ToolParameter(type="string", description="Text content to write", required=True),
        "overwrite": ToolParameter(type="boolean", description="Allow overwriting existing file", default=True),
    },
)
async def write_file(path: str, content: str, overwrite: bool = True) -> Dict[str, Any]:
    safe_path = _resolve_safe_path(path)
    if safe_path.exists() and not overwrite:
        raise FileExistsError(f"File already exists and overwrite is set to False: {path}")

    safe_path.parent.mkdir(parents=True, exist_ok=True)
    safe_path.write_text(content, encoding="utf-8")
    return {
        "path": str(safe_path),
        "bytes_written": len(content.encode("utf-8")),
        "created": not safe_path.exists(),
    }


@jarvis_tool(
    tool_id="search_files",
    name="Search Files",
    description="Search files for a keyword pattern within the workspace.",
    category="filesystem",
    permission_tier=PermissionTier.SAFE,
    parameters={
        "pattern": ToolParameter(type="string", description="Text or substring to search for", required=True),
        "directory": ToolParameter(type="string", description="Directory to search within", default="."),
        "file_pattern": ToolParameter(type="string", description="File glob pattern, e.g. *.py", default="*"),
    },
)
async def search_files(pattern: str, directory: str = ".", file_pattern: str = "*") -> Dict[str, Any]:
    safe_dir = _resolve_safe_path(directory)
    matches = []

    for p in safe_dir.rglob(file_pattern):
        if p.is_file() and not any(part.startswith(".") for part in p.parts):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
                if pattern in text:
                    # Find matching lines
                    lines = text.splitlines()
                    matching_lines = [
                        {"line": i + 1, "text": line.strip()}
                        for i, line in enumerate(lines)
                        if pattern in line
                    ][:10]
                    matches.append({
                        "path": str(p.relative_to(safe_dir)),
                        "matches": matching_lines,
                    })
            except Exception:
                continue

    return {"query": pattern, "results": matches, "match_count": len(matches)}
