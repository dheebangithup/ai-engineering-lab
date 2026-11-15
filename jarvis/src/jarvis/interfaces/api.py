"""
FastAPI REST API Gateway & Control Server for J.A.R.V.I.S.
Exposes the agent chat interface, system status, and UI management endpoints
to dynamically control LLM providers, tools, and external MCP servers.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jarvis.config.provider_config import ProviderInstanceConfig
from jarvis.core.jarvis import Jarvis
from jarvis.core.schemas import JarvisRequest, JarvisResponse
from jarvis.interfaces.schemas import (
    ChatRequest,
    PermissionApprovalRequest,
    SystemStatusResponse,
    TestProviderConnectionRequest,
    TestProviderConnectionResponse,
    UpdateFallbackChainRequest,
)
from jarvis.logger import get_logger
from jarvis.mcp.schemas import MCPServerConfig
from jarvis.tools.schemas import ToolDefinition

logger = get_logger("interfaces.api")

# UI frontend dist directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
FRONTEND_ASSETS = FRONTEND_DIST / "assets"
INDEX_HTML = FRONTEND_DIST / "index.html"

# Global singleton Jarvis instance
_jarvis_instance: Jarvis | None = None


def get_jarvis() -> Jarvis:
    global _jarvis_instance
    if _jarvis_instance is None:
        _jarvis_instance = Jarvis()
    return _jarvis_instance


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle startup and shutdown handler."""
    jarvis = get_jarvis()
    logger.info("Starting J.A.R.V.I.S. API Server...")
    await jarvis.initialize()
    yield
    logger.info("Shutting down J.A.R.V.I.S. API Server...")
    await jarvis.shutdown()


app = FastAPI(
    title="J.A.R.V.I.S. Core API",
    description="REST API Gateway and Control Center for the J.A.R.V.I.S. Personal AI Agent System",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for future frontend/UI dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static assets for React UI dashboard
if FRONTEND_ASSETS.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS), name="assets")
if FRONTEND_DIST.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIST), name="static")


# =============================================================================
# 0. Web UI Dashboard Endpoints
# =============================================================================

@app.get("/", response_class=HTMLResponse, summary="Serve J.A.R.V.I.S. Web Dashboard")
@app.get("/ui", response_class=HTMLResponse, summary="Serve J.A.R.V.I.S. Web Dashboard")
async def serve_ui() -> HTMLResponse:
    if INDEX_HTML.exists():
        return HTMLResponse(content=INDEX_HTML.read_text(encoding="utf-8"))
    return HTMLResponse(
        content="<h1>J.A.R.V.I.S. API Online</h1><p>Frontend build not found. Run <code>cd frontend && npm run build</code> or visit <a href='/docs'>/docs</a>.</p>"
    )


# =============================================================================
# 1. Main Agent Chat Endpoint
# =============================================================================

@app.post("/v1/chat", response_model=JarvisResponse, summary="Send a query to J.A.R.V.I.S.")
async def chat_endpoint(request: ChatRequest) -> JarvisResponse:
    jarvis = get_jarvis()
    try:
        response = await jarvis.process(
            JarvisRequest(
                query=request.query,
                session_id=request.session_id,
                context_override=request.context_override,
                preferred_provider=request.preferred_provider,
                model_override=request.model_override,
            )
        )
        return response
    except Exception as e:
        logger.error(f"Error in /v1/chat: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"J.A.R.V.I.S. execution error: {str(e)}",
        )


# =============================================================================
# 2. System Status & Health
# =============================================================================

@app.get("/v1/status", response_model=SystemStatusResponse, summary="Inspect system health & status")
async def status_endpoint() -> SystemStatusResponse:
    jarvis = get_jarvis()
    health_results = jarvis.provider_gateway.get_providers_health()
    configured_mcp = [s.server_id for s in jarvis.mcp_manager.list_configured_servers()]

    return SystemStatusResponse(
        status="operational",
        workspace_root=str(jarvis.workspace.root_dir),
        active_providers=jarvis.provider_gateway.list_active_providers(),
        provider_health=health_results,
        total_tools=len(jarvis.tools_gateway.registry),
        tool_categories=jarvis.tools_gateway.registry.list_categories(),
        mcp_servers=configured_mcp,
    )


# =============================================================================
# 3. LLM Provider Management Endpoints (For UI)
# =============================================================================

@app.get("/v1/settings/providers", summary="List all configured LLM providers and fallback chains")
async def list_providers_endpoint() -> Dict[str, Any]:
    jarvis = get_jarvis()
    cfg = jarvis.provider_gateway.store.load_config(force_reload=True)
    return {
        "providers": {k: v.model_dump() for k, v in cfg.providers.items()},
        "fallback_chains": {k.value: v for k, v in cfg.fallback_chains.items()},
    }


@app.post(
    "/v1/settings/providers/test_connection",
    response_model=TestProviderConnectionResponse,
    summary="Test connectivity and verify API token for an LLM provider endpoint",
)
async def test_provider_connection_endpoint(
    request: TestProviderConnectionRequest,
) -> TestProviderConnectionResponse:
    from jarvis.llm.connection_tester import test_llm_provider_connectivity
    return await test_llm_provider_connectivity(request)


@app.get("/v1/settings/providers/{provider_id}", summary="Get a specific provider configuration")
async def get_provider_endpoint(provider_id: str) -> Dict[str, Any]:
    jarvis = get_jarvis()
    cfg = jarvis.provider_gateway.store.load_config(force_reload=True)
    if provider_id not in cfg.providers:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found")
    return cfg.providers[provider_id].model_dump()


@app.post("/v1/settings/fallback_chains", summary="Update fallback chain priority order for a role")
async def update_fallback_chain_endpoint(request: UpdateFallbackChainRequest) -> Dict[str, Any]:
    jarvis = get_jarvis()
    jarvis.provider_gateway.store.set_fallback_chain(request.role, request.provider_ids)
    jarvis.provider_gateway.reload()
    return {
        "message": f"Fallback chain for role '{request.role.value}' updated successfully",
        "role": request.role.value,
        "provider_ids": request.provider_ids,
    }


@app.post("/v1/settings/providers", summary="Add or update an LLM provider dynamically")
async def add_provider_endpoint(provider_cfg: ProviderInstanceConfig) -> Dict[str, str]:
    jarvis = get_jarvis()
    jarvis.provider_gateway.store.add_or_update_provider(provider_cfg)
    jarvis.provider_gateway.reload()
    return {"message": f"Provider '{provider_cfg.provider_id}' successfully updated"}


@app.delete("/v1/settings/providers/{provider_id}", summary="Remove an LLM provider")
async def remove_provider_endpoint(provider_id: str) -> Dict[str, str]:
    jarvis = get_jarvis()
    success = jarvis.provider_gateway.store.remove_provider(provider_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found")
    jarvis.provider_gateway.reload()
    return {"message": f"Provider '{provider_id}' removed successfully"}


# =============================================================================
# 4. MCP Server Management Endpoints (For UI)
# =============================================================================

@app.get("/v1/settings/mcp", summary="List all configured external MCP servers")
async def list_mcp_servers_endpoint() -> Dict[str, Any]:
    jarvis = get_jarvis()
    cfg = jarvis.mcp_manager.store.load_config()
    return {"servers": {k: v.model_dump() for k, v in cfg.servers.items()}}


@app.post("/v1/settings/mcp", summary="Add, update, or enable/disable an MCP server dynamically")
async def add_mcp_server_endpoint(server_cfg: MCPServerConfig) -> Dict[str, str]:
    jarvis = get_jarvis()
    success = await jarvis.mcp_manager.add_or_update_server(server_cfg)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to connect and bridge MCP server '{server_cfg.server_id}'")
    return {"message": f"MCP server '{server_cfg.server_id}' successfully configured and bridged"}


@app.delete("/v1/settings/mcp/{server_id}", summary="Remove an external MCP server")
async def remove_mcp_server_endpoint(server_id: str) -> Dict[str, str]:
    jarvis = get_jarvis()
    success = await jarvis.mcp_manager.remove_server(server_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"MCP server '{server_id}' not found")
    return {"message": f"MCP server '{server_id}' removed and unbridged"}


# =============================================================================
# 5. Tools & Permissions Endpoints
# =============================================================================

@app.get("/v1/tools", summary="List all registered tools and their security tiers")
async def list_tools_endpoint(category: str | None = None) -> List[Dict[str, Any]]:
    jarvis = get_jarvis()
    tools = jarvis.tools_gateway.list_tools(category=category)
    return [
        {
            "tool_id": t.tool_id,
            "name": t.name,
            "category": t.category,
            "description": t.description,
            "permission_tier": t.permission_tier.value,
            "requires_approval": t.requires_approval,
            "parameters": {k: v.model_dump() for k, v in t.parameters.items()},
        }
        for t in tools
    ]


@app.post("/v1/permissions/approve", response_model=JarvisResponse, summary="Approve or deny a pending sensitive action")
async def approve_permission_endpoint(request: PermissionApprovalRequest) -> JarvisResponse:
    jarvis = get_jarvis()
    return await jarvis.approve_pending_permission(
        session_id=request.session_id,
        approved=request.approved,
        action_token=request.action_token,
    )
