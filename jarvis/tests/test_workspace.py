"""
Workspace Single Source of Truth (SSOT) Test Suite.
Validates centralized path resolution, storage isolation for coding agents,
dynamic sibling discovery, and directory initialization.
"""

from pathlib import Path
import pytest

from jarvis.workspace import Workspace, get_workspace, set_active_workspace


def test_workspace_paths_anchor_to_root(tmp_path: Path):
    """Verify that all system subpaths are deterministically rooted under the workspace."""
    custom_root = tmp_path / "jarvis_sandbox"
    ws = Workspace.from_root(custom_root).initialize()

    # Root
    assert ws.root_dir == custom_root.resolve()
    assert ws.root_dir.exists()

    # Settings & configs
    assert ws.settings_dir == custom_root / "settings"
    assert ws.settings_dir.exists()
    assert ws.providers_config_path == custom_root / "settings" / "providers.json"
    assert ws.mcp_config_path == custom_root / "settings" / "mcp_servers.json"
    assert ws.agent_config_path == custom_root / "settings" / "agent_config.json"

    # Memory storage
    assert ws.memory_dir == custom_root / "memory"
    assert ws.memory_dir.exists()
    assert ws.memory_cache_dir == custom_root / "memory" / "cache"
    assert ws.memory_cache_dir.exists()
    assert ws.memory_audit_file == custom_root / "memory" / "audit.jsonl"

    # Code workspace (coding agents sandbox)
    assert ws.code_workspace_dir == custom_root / "code_workspace"
    assert ws.code_workspace_dir.exists()
    assert ws.artifacts_dir == custom_root / "code_workspace" / "artifacts"
    assert ws.artifacts_dir.exists()

    # Logs
    assert ws.logs_dir == custom_root / "logs"
    assert ws.logs_dir.exists()
    assert ws.app_log_path == custom_root / "logs" / "app.log"
    assert ws.jarvis_log_path == custom_root / "logs" / "jarvis.log"

    # Storage & Sessions
    assert ws.storage_dir == custom_root / "storage"
    assert ws.storage_dir.exists()
    assert ws.sessions_db_path == custom_root / "storage" / "sessions.db"


def test_dynamic_sibling_discovery():
    """Verify that sibling projects like strata-memory are located dynamically without hardcoded paths."""
    sibling = Workspace.get_sibling_project("strata-memory")
    assert sibling is not None, "strata-memory sibling project should be dynamically located"
    assert sibling.exists()
    assert (sibling / "pyproject.toml").exists() or (sibling / ".env").exists()


def test_set_active_workspace_runtime_override(tmp_path: Path):
    """Verify that set_active_workspace reconfigures the global singleton cleanly."""
    sandbox = tmp_path / "runtime_agent_ws"
    ws = set_active_workspace(sandbox)

    assert get_workspace().root_dir == sandbox.resolve()
    assert ws.code_workspace_dir.exists()
    assert ws.settings_dir.exists()
