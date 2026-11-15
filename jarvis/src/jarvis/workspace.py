"""
Single Source of Truth (SSOT) Workspace Manager for J.A.R.V.I.S.
Provides centralized, deterministic path resolution and directory management for:
 - Configuration & Settings (providers.json, mcp_servers.json, agent_config.json)
 - Agent Long-Term & Short-Term Memory Storage (snapshots, audit logs, caches)
 - Code Execution Workspace (sandboxed environment for coding agents & file tools)
 - Logging (app.log, jarvis.log)
 - Session Storage & Checkpoints
"""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional


DEFAULT_WORKSPACE_DIR = Path.home() / ".jarvis"


@dataclass
class Workspace:
    """The Single Source of Truth for all J.A.R.V.I.S. runtime paths and storage."""

    root_dir: Path

    @classmethod
    def from_root(cls, root: Path | str) -> "Workspace":
        return cls(root_dir=Path(root).resolve())

    # -------------------------------------------------------------------------
    # 1. Settings & Configurations
    # -------------------------------------------------------------------------
    @property
    def settings_dir(self) -> Path:
        """Directory housing all persistent system configurations (UI-ready)."""
        return self.root_dir / "settings"

    @property
    def providers_config_path(self) -> Path:
        """Path to LLM providers and fallback chains configuration."""
        return self.settings_dir / "providers.json"

    @property
    def mcp_config_path(self) -> Path:
        """Path to external MCP servers and security tier configuration."""
        return self.settings_dir / "mcp_servers.json"

    @property
    def agent_config_path(self) -> Path:
        """Path to agent behavior, model role assignments, and persona configs."""
        return self.settings_dir / "agent_config.json"

    # -------------------------------------------------------------------------
    # 2. Memory & Context Storage
    # -------------------------------------------------------------------------
    @property
    def memory_dir(self) -> Path:
        """Root directory for agent memory storage, audit trails, and snapshots."""
        return self.root_dir / "memory"

    @property
    def memory_cache_dir(self) -> Path:
        """High-speed local cache for recalled memory contexts."""
        return self.memory_dir / "cache"

    @property
    def memory_audit_file(self) -> Path:
        """Audit trail logging all memory operations (ingest, supersedes, deletes)."""
        return self.memory_dir / "audit.jsonl"

    # -------------------------------------------------------------------------
    # 3. Code & Tool Execution Sandbox (Coding Agents Workspace)
    # -------------------------------------------------------------------------
    @property
    def code_workspace_dir(self) -> Path:
        """
        The dedicated execution sandbox for coding agents and file tools.
        All project creation, code generation, and file inspection operate here,
        ensuring clean traceability and preventing system directory pollution.
        """
        return self.root_dir / "code_workspace"

    @property
    def artifacts_dir(self) -> Path:
        """Directory where generated plans, code artifacts, and reports are saved."""
        return self.code_workspace_dir / "artifacts"

    # -------------------------------------------------------------------------
    # 4. Centralized Logging
    # -------------------------------------------------------------------------
    @property
    def logs_dir(self) -> Path:
        """Directory for system and agent trace logs."""
        return self.root_dir / "logs"

    @property
    def app_log_path(self) -> Path:
        """Global application log file (rotating)."""
        return self.logs_dir / "app.log"

    @property
    def jarvis_log_path(self) -> Path:
        """Agent reasoning and tool trace log file (rotating)."""
        return self.logs_dir / "jarvis.log"

    # -------------------------------------------------------------------------
    # 5. Session State & Checkpoints
    # -------------------------------------------------------------------------
    @property
    def storage_dir(self) -> Path:
        """Directory for conversation history checkpoints and agent session states."""
        return self.root_dir / "storage"

    @property
    def sessions_db_path(self) -> Path:
        """Path to SQLite session database."""
        return self.storage_dir / "sessions.db"

    # -------------------------------------------------------------------------
    # Lifecycle Management
    # -------------------------------------------------------------------------
    def initialize(self) -> "Workspace":
        """Bootstrap and verify the entire directory tree."""
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.memory_cache_dir.mkdir(parents=True, exist_ok=True)
        self.code_workspace_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        return self

    # -------------------------------------------------------------------------
    # Dynamic Environment & Sibling Discovery (Zero Hardcoding)
    # -------------------------------------------------------------------------
    @staticmethod
    def get_project_root() -> Path:
        """Returns the absolute path to this jarvis project repository."""
        return Path(__file__).resolve().parents[2]

    @staticmethod
    def get_sibling_project(project_name: str) -> Optional[Path]:
        """
        Dynamically locate a sibling project directory (e.g. 'strata-memory')
        relative to the parent lab directory without hardcoding user home paths.
        """
        # 1. Check explicit environment override
        env_var_name = f"{project_name.upper().replace('-', '_')}_DIR"
        env_path = os.getenv(env_var_name)
        if env_path and Path(env_path).exists():
            return Path(env_path).resolve()

        # 2. Check sibling directory in the same parent folder
        lab_dir = Workspace.get_project_root().parent
        candidate = lab_dir / project_name
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()

        return None


_active_workspace: Optional[Workspace] = None


def get_workspace() -> Workspace:
    """Return the active singleton Workspace (Single Source of Truth)."""
    global _active_workspace
    if _active_workspace is None:
        raw_env_dir = os.getenv("JARVIS_WORKSPACE")
        target_dir = Path(raw_env_dir).resolve() if raw_env_dir else DEFAULT_WORKSPACE_DIR
        _active_workspace = Workspace.from_root(target_dir).initialize()
    return _active_workspace


def set_active_workspace(workspace_dir: Path | str) -> Workspace:
    """Override the active workspace root at runtime (e.g. for testing or UI switching)."""
    global _active_workspace
    _active_workspace = Workspace.from_root(workspace_dir).initialize()
    return _active_workspace


# Backward compatibility aliases
default_workspace = get_workspace
initialize_workspace = lambda ws=None: (ws or get_workspace()).initialize()
