"""
MCP Server Configuration Store.
Persists configured MCP servers in JSON format (e.g. workspace/settings/mcp_servers.json).
Allows runtime additions, edits, and deletions ready for the UI management screen.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from jarvis.config.settings import get_settings
from jarvis.logger import get_logger
from jarvis.mcp.schemas import MCPRegistryConfig, MCPServerConfig, MCPTransportType
from jarvis.tools.schemas import PermissionTier
from jarvis.workspace import default_workspace

logger = get_logger("mcp.store")


class MCPStore:
    """Manages reading, writing, and seeding external MCP server configurations."""

    def __init__(self, settings_file: Optional[Path] = None):
        if settings_file is None:
            ws = default_workspace().initialize()
            self.settings_file = ws.settings_dir / "mcp_servers.json"
        else:
            self.settings_file = Path(settings_file)

        self._config: Optional[MCPRegistryConfig] = None

    def load_config(self) -> MCPRegistryConfig:
        """Load MCP config from file, or initialize with seed defaults."""
        if self._config is not None:
            return self._config

        if self.settings_file.exists():
            try:
                raw_data = json.loads(self.settings_file.read_text(encoding="utf-8"))
                self._config = MCPRegistryConfig.model_validate(raw_data)
                logger.info(f"Loaded MCP server configurations from {self.settings_file}")
                return self._config
            except Exception as e:
                logger.error(f"Failed to parse {self.settings_file}, creating seed config: {e}")

        # Seed initial MCP servers
        self._config = self._create_seed_config()
        self.save_config(self._config)
        return self._config

    def save_config(self, config: MCPRegistryConfig) -> None:
        """Persist MCP server configuration to the settings file."""
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings_file.write_text(
            config.model_dump_json(indent=2),
            encoding="utf-8",
        )
        self._config = config
        logger.info(f"Saved MCP server configuration to {self.settings_file}")

    def add_or_update_server(self, server: MCPServerConfig) -> None:
        """Add or update an MCP server configuration."""
        cfg = self.load_config()
        cfg.servers[server.server_id] = server
        self.save_config(cfg)

    def remove_server(self, server_id: str) -> bool:
        """Remove an MCP server configuration."""
        cfg = self.load_config()
        if server_id not in cfg.servers:
            return False
        del cfg.servers[server_id]
        self.save_config(cfg)
        return True

    def _create_seed_config(self) -> MCPRegistryConfig:
        """Seed default MCP configurations including Strata Cognitive Memory."""
        servers: Dict[str, MCPServerConfig] = {}

        # Detect strata-mcp executable path
        sibling_strata_dir = Path("/Users/dheeban/Documents/my_projects/ai-engineering-lab/strata-memory")
        strata_mcp_bin = sibling_strata_dir / ".venv" / "bin" / "strata-mcp"
        command = str(strata_mcp_bin) if strata_mcp_bin.exists() else "strata-mcp"

        # Read env vars from sibling .env if available for initial seed
        strata_env: Dict[str, str] = {}
        strata_dotenv = sibling_strata_dir / ".env"
        if strata_dotenv.exists():
            for line in strata_dotenv.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    strata_env[k.strip()] = v.strip().strip('"').strip("'")

        # Explicit security tiers as requested:
        # delete, purge, prune, edit -> ALWAYS PERMISSION NEEDED (DANGEROUS)
        security_overrides: Dict[str, PermissionTier] = {
            "memory_recall": PermissionTier.SAFE,
            "memory_ingest": PermissionTier.SENSITIVE,
            "memory_store_explicit": PermissionTier.SENSITIVE,
            "memory_feedback": PermissionTier.SAFE,
            "memory_edit": PermissionTier.DANGEROUS,
            "memory_delete": PermissionTier.DANGEROUS,
            "memory_prune": PermissionTier.DANGEROUS,
            "memory_purge_namespace": PermissionTier.DANGEROUS,
        }

        approval_overrides: Dict[str, bool] = {
            "memory_edit": True,
            "memory_delete": True,
            "memory_prune": True,
            "memory_purge_namespace": True,
        }

        servers["strata-memory"] = MCPServerConfig(
            server_id="strata-memory",
            name="Strata Cognitive 4-Pillar Memory Engine",
            transport=MCPTransportType.STDIO,
            command=command,
            args=["--transport", "stdio"],
            env=strata_env,
            enabled=True,
            description="4-pillar cognitive memory engine (semantic, episodic, procedural, entity graph).",
            security_overrides=security_overrides,
            approval_overrides=approval_overrides,
        )

        return MCPRegistryConfig(servers=servers)
