import asyncio
import os
from jarvis import config
from jarvis.decision.decision_engine import DecisionEngine
from jarvis.llm.provider_gateway import ProviderGateway
from jarvis.logger import get_logger, setup_logging
from jarvis.mcp.mcp_manager import MCPManager
from jarvis.tools.implementations.filesystem import (
    list_files,
    read_file,
    search_files,
    write_file,
)
from jarvis.tools.implementations.shell import run_command
from jarvis.tools.meta_tools import create_gateway_meta_tools
from jarvis.tools.permissions import PermissionInterceptor
from jarvis.tools.tool_gateway import ToolsGateway

setup_logging()
logger = get_logger("jarvis.main")


def check_langsmith_connection() -> None:
    """Verifies LangSmith environment configuration and connectivity."""
    tracing = os.getenv("LANGSMITH_TRACING", "").lower() in ("true", "1", "t")
    api_key = os.getenv("LANGSMITH_API_KEY")
    endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    project = os.getenv("LANGSMITH_PROJECT", "jarvis")

    logger.info(f"LangSmith Tracing Enabled: {tracing}")
    logger.info(f"LangSmith Project: {project}")
    logger.info(f"LangSmith Endpoint: {endpoint}")

    if not api_key:
        logger.warning("LANGSMITH_API_KEY is not set in environment.")
        return

    try:
        from langsmith import Client
        _ = Client(api_url=endpoint, api_key=api_key)
        logger.info("Successfully connected to LangSmith.")
    except Exception as e:
        logger.warning(f"Could not connect to LangSmith client: {e}")


async def bootstrap_jarvis() -> None:
    """Initialize J.A.R.V.I.S. subsystems: Provider Gateway, Decision Engine, Tools Gateway, and MCP Manager."""
    check_langsmith_connection()
    logger.info("Bootstrapping J.A.R.V.I.S. Core Systems...")

    # 1. Initialize Provider Gateway
    gateway = ProviderGateway()
    active_providers = gateway.list_active_providers()
    logger.info(f"Provider Gateway loaded with active providers: {active_providers}")

    # 2. Check Provider Health Status
    health_results = await gateway.check_all_providers_health()
    for pid, health in health_results.items():
        lat = f"{health.latency_ms:.1f}ms" if health.latency_ms is not None else "N/A"
        logger.info(f"Provider '{pid}': status={health.status.value}, latency={lat}")

    # 3. Initialize Decision Engine with dedicated Decision Model (<5ms)
    decision_engine = DecisionEngine(provider_gateway=gateway)
    logger.info("Decision Engine initialized with sub-5ms Decision Model.")

    # 4. Initialize Tools Gateway & Register built-in tools
    permission_interceptor = PermissionInterceptor()
    tools_gateway = ToolsGateway(permission_interceptor=permission_interceptor)
    tools_gateway.register_tool(list_files)
    tools_gateway.register_tool(read_file)
    tools_gateway.register_tool(write_file)
    tools_gateway.register_tool(search_files)
    tools_gateway.register_tool(run_command)

    # 5. Initialize Multi-Server MCP Manager (connects Strata Memory & any external servers)
    mcp_manager = MCPManager(tools_gateway=tools_gateway)
    bridged_mcp = await mcp_manager.initialize_servers()
    logger.info(f"MCP Manager bridged {sum(len(tools) for tools in bridged_mcp.values())} external tools across servers: {list(bridged_mcp.keys())}")

    # 6. Create the 3 Meta-Tools for Agents (Uber Architecture)
    meta_tools = create_gateway_meta_tools(tools_gateway)
    total_tools = len(tools_gateway.registry)
    categories = tools_gateway.registry.list_categories()
    logger.info(f"Tools Gateway active with {total_tools} total tools across categories {categories}")
    logger.info(f"Uber Meta-Tools created for agent exposure: {[m._jarvis_tool_def.tool_id for m in meta_tools]}")

    # 7. Demonstrate Meta-Tool Search across both built-in and MCP memory tools
    search_fn = meta_tools[0]
    discovered = await search_fn(query="recall past user facts and projects")
    logger.info(f"Meta-tool search for 'recall past user facts': {[t['tool_id'] for t in discovered]}")

    await mcp_manager.shutdown()
    await gateway.close()
    logger.info("J.A.R.V.I.S. Core Systems (Phase 1, 2, 3) ready for Phase 4 (Agent Hub & Prompt Hub).")


def main() -> None:
    asyncio.run(bootstrap_jarvis())


if __name__ == "__main__":
    main()
