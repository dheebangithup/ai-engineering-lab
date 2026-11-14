"""
Workspace environment management for J.A.R.V.I.S.
Configures and initializes workspace paths, runtime logs, cache, and settings directories.
"""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional


DEFAULT_WORKSPACE_DIR = Path.home() / ".jarvis"


@dataclass
class Workspace:
    """Represents the J.A.R.V.I.S. working directory environment."""

    root_dir: Path
    logs_dir: Path
    settings_dir: Path
    cache_dir: Path
    data_dir: Path

    @classmethod
    def from_root(cls, root: Path | str) -> "Workspace":
        root_path = Path(root).resolve()
        return cls(
            root_dir=root_path,
            logs_dir=root_path / "logs",
            settings_dir=root_path / "settings",
            cache_dir=root_path / "cache",
            data_dir=root_path / "data",
        )

    def initialize(self) -> "Workspace":
        """Ensure all required runtime directories exist."""
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self


_default_ws: Optional[Workspace] = None


def default_workspace() -> Workspace:
    """Return the singleton default workspace."""
    global _default_ws
    if _default_ws is None:
        raw_env_dir = os.getenv("JARVIS_WORKSPACE")
        target_dir = Path(raw_env_dir).resolve() if raw_env_dir else DEFAULT_WORKSPACE_DIR
        _default_ws = Workspace.from_root(target_dir)
    return _default_ws


def initialize_workspace(workspace: Optional[Workspace] = None) -> Workspace:
    """Initialize directories for a workspace instance or the default."""
    ws = workspace or default_workspace()
    return ws.initialize()
