"""
Generic MCP Client Wrapper for J.A.R.V.I.S.
Handles communication with external MCP servers over stdio or SSE transports.
"""

import asyncio
import os
from typing import Any, Dict, List, Optional
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
import mcp.types as types
from jarvis.logger import get_logger
from jarvis.mcp.schemas import MCPServerConfig, MCPTransportType

logger = get_logger("mcp.client")


class MCPClientWrapper:
    """Manages an active connection to an external Model Context Protocol server."""

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.server_id = config.server_id
        self._session: Optional[ClientSession] = None
        self._stdio_cm = None
        self._exit_stack = None
        self._is_connected = False
        self._tools_cache: List[types.Tool] = []

    async def connect(self) -> bool:
        """Establish connection with the MCP server and run initialization handshake."""
        if self._is_connected and self._session:
            return True

        if self.config.transport == MCPTransportType.STDIO:
            if not self.config.command:
                logger.error(f"Cannot start stdio MCP server '{self.server_id}': No command provided")
                return False

            env_vars = os.environ.copy()
            if self.config.env:
                env_vars.update(self.config.env)

            server_params = StdioServerParameters(
                command=self.config.command,
                args=self.config.args,
                env=env_vars,
            )

            try:
                # Use contextlib.AsyncExitStack to hold the stdio streams and session open
                from contextlib import AsyncExitStack
                self._exit_stack = AsyncExitStack()

                # Enter stdio transport
                read_stream, write_stream = await self._exit_stack.enter_async_context(
                    stdio_client(server_params)
                )

                # Enter client session
                self._session = await self._exit_stack.enter_async_context(
                    ClientSession(read_stream, write_stream)
                )

                # Perform initialization handshake
                await self._session.initialize()
                self._is_connected = True
                logger.info(f"Successfully connected to MCP server '{self.server_id}' via stdio")
                return True

            except Exception as e:
                logger.error(f"Failed to connect to MCP server '{self.server_id}': {e}", exc_info=True)
                await self.disconnect()
                return False

        else:
            logger.warning(f"Transport '{self.config.transport}' not yet implemented for '{self.server_id}'")
            return False

    async def list_tools(self) -> List[types.Tool]:
        """Fetch list of tools offered by the MCP server."""
        if not self._is_connected or not self._session:
            connected = await self.connect()
            if not connected or not self._session:
                return []

        try:
            result = await self._session.list_tools()
            self._tools_cache = result.tools
            logger.info(f"MCP server '{self.server_id}' reported {len(self._tools_cache)} tools: {[t.name for t in self._tools_cache]}")
            return self._tools_cache
        except Exception as e:
            logger.error(f"Failed to list tools from MCP server '{self.server_id}': {e}")
            return []

    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Call a specific tool on the MCP server and return parsed output."""
        if not self._is_connected or not self._session:
            connected = await self.connect()
            if not connected or not self._session:
                raise ConnectionError(f"MCP server '{self.server_id}' is not connected")

        args = arguments or {}
        try:
            result = await self._session.call_tool(name, arguments=args)
            
            # Format output content blocks
            formatted_contents = []
            for item in result.content:
                if hasattr(item, "text"):
                    formatted_contents.append(item.text)
                else:
                    formatted_contents.append(str(item))

            joined = "\n".join(formatted_contents)
            return {
                "output": joined,
                "is_error": getattr(result, "isError", False),
                "raw_content": [c.model_dump() if hasattr(c, "model_dump") else str(c) for c in result.content],
            }
        except Exception as e:
            logger.error(f"Error calling tool '{name}' on MCP server '{self.server_id}': {e}")
            raise e

    async def disconnect(self) -> None:
        """Gracefully close session and release process streams."""
        self._is_connected = False
        self._session = None
        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            except Exception as e:
                logger.debug(f"Error while disconnecting MCP server '{self.server_id}': {e}")
            finally:
                self._exit_stack = None
        logger.info(f"Disconnected from MCP server '{self.server_id}'")
