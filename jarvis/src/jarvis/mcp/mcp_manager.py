"""
Central MCP Manager for J.A.R.V.I.S.
Manages multiple external MCP servers (Strata Memory, GitHub, Postgres, etc.),
their lifecycles, and their bridging into the central ToolsGateway.
"""

from typing import Dict, List, Optional
from jarvis.logger import get_logger
from jarvis.mcp.bridge import bridge_mcp_server_to_gateway
from jarvis.mcp.mcp_client import MCPClientWrapper
from jarvis.mcp.mcp_store import MCPStore
from jarvis.mcp.schemas import MCPServerConfig
from jarvis.tools.tool_gateway import ToolsGateway

logger = get_logger("mcp.manager")


class MCPManager:
    """Manages multi-server MCP integrations for J.A.R.V.I.S."""

    def __init__(
        self,
        tools_gateway: ToolsGateway,
        store: Optional[MCPStore] = None,
    ):
        self.gateway = tools_gateway
        self.store = store or MCPStore()
        self._clients: Dict[str, MCPClientWrapper] = {}

    def get_client(self, server_id: str) -> Optional[MCPClientWrapper]:
        """Get an active MCP client wrapper by server ID."""
        return self._clients.get(server_id)

    def list_configured_servers(self) -> List[MCPServerConfig]:
        """List all configured MCP servers."""
        cfg = self.store.load_config()
        return list(cfg.servers.values())

    async def initialize_servers(self) -> Dict[str, List[str]]:
        """
        Connect to all enabled MCP servers and bridge their tools into the ToolsGateway.
        Returns: Dict mapping server_id to list of bridged tool IDs.
        """
        config = self.store.load_config()
        results: Dict[str, List[str]] = {}

        for server_id, server_cfg in config.servers.items():
            if not server_cfg.enabled:
                logger.info(f"MCP server '{server_id}' is disabled, skipping")
                continue

            try:
                client = MCPClientWrapper(server_cfg)
                connected = await client.connect()
                if not connected:
                    logger.warning(f"Could not connect to MCP server '{server_id}'")
                    results[server_id] = []
                    continue

                self._clients[server_id] = client
                bridged = await bridge_mcp_server_to_gateway(client, self.gateway)
                results[server_id] = bridged
                logger.info(f"Initialized MCP server '{server_id}' with {len(bridged)} tools bridged")

            except Exception as e:
                logger.error(f"Error initializing MCP server '{server_id}': {e}", exc_info=True)
                results[server_id] = []

        return results

    async def add_or_update_server(self, server_cfg: MCPServerConfig) -> bool:
        """Add or update an MCP server and bridge its tools at runtime (for UI)."""
        self.store.add_or_update_server(server_cfg)
        
        # If already running, disconnect first
        if server_cfg.server_id in self._clients:
            await self._clients[server_cfg.server_id].disconnect()
            del self._clients[server_cfg.server_id]

        if not server_cfg.enabled:
            return True

        client = MCPClientWrapper(server_cfg)
        connected = await client.connect()
        if connected:
            self._clients[server_cfg.server_id] = client
            await bridge_mcp_server_to_gateway(client, self.gateway)
            return True
        return False

    async def remove_server(self, server_id: str) -> bool:
        """Remove an MCP server and unregister its tools."""
        if server_id in self._clients:
            client = self._clients[server_id]
            for t in client._tools_cache:
                self.gateway.registry.unregister(t.name)
            await client.disconnect()
            del self._clients[server_id]

        return self.store.remove_server(server_id)

    async def shutdown(self) -> None:
        """Disconnect and clean up all active MCP server connections."""
        logger.info(f"Shutting down {len(self._clients)} active MCP clients...")
        for server_id, client in list(self._clients.items()):
            try:
                await client.disconnect()
            except Exception as e:
                logger.debug(f"Error disconnecting '{server_id}': {e}")
        self._clients.clear()
