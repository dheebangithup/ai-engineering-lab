import argparse
import hmac
import json
import logging
import sys
from typing import Annotated, Any, Dict, List, Literal, Optional
import httpx
from pydantic import Field
from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from strata.config import settings
from strata.db import close_db_pool, ensure_db_ready_and_migrate, get_db_pool
from strata.neon_control import maybe_suspend_neon_compute
from strata.service import (
    svc_memory_delete,
    svc_memory_edit,
    svc_memory_feedback,
    svc_memory_ingest,
    svc_memory_prune,
    svc_memory_purge_namespace,
    svc_memory_recall,
    svc_memory_store_explicit,
    svc_working_memory_add_tool_output,
    svc_working_memory_get,
    svc_working_memory_unprotect,
)

# Direct all logs to stderr to keep stdout pure for JSON-RPC stdio transport
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("strata.mcp_server")


class BearerAuthMiddleware:
    """Pure ASGI Bearer token guard for HTTP-exposed MCP routes (zero stream buffering)."""

    EXEMPT_PATHS = {"/health", "/ready"}

    def __init__(self, app: Any, token: str) -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope: Dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http" or scope.get("path") in self.EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        auth_val = headers.get(b"authorization", b"").decode("latin-1")
        expected = f"Bearer {self.token}"
        if not auth_val or not hmac.compare_digest(auth_val, expected):
            resp = JSONResponse({"error": "Unauthorized: invalid or missing Bearer token"}, status_code=401)
            await resp(scope, receive, send)
            return

        await self.app(scope, receive, send)


@lifespan
async def strata_mcp_lifespan(server: FastMCP):
    """Initializes database readiness/migrations on startup and cleans up pool on shutdown."""
    if settings.auto_migrate:
        await ensure_db_ready_and_migrate(auto_migrate=True)
    yield {}
    await close_db_pool()
    await maybe_suspend_neon_compute()


mcp = FastMCP(
    name="Strata Memory Engine",
    version="0.1.0",
    lifespan=strata_mcp_lifespan,
    instructions="""
Strata is a 4-pillar cognitive memory engine backed by Neon Serverless PostgreSQL.
It provides long-term persistence across 4 distinct cognitive layers:
1. Semantic Layer: Atomic facts, user configurations, preferences, and domain truths with bi-temporal validity.
2. Episodic Layer: Timestamped execution traces, situations, actions, outcomes, and utility scores.
3. Procedural Layer: Versioned workflows, runbooks, and skills with Bayesian ranking and self-healing.
4. Entity Graph Layer: Bi-temporal property graph of connected people, projects, servers, and services.

RECOMMENDED AGENT WORKFLOW:
- CALL `memory_recall` BEFORE answering complex questions to retrieve active context and runbooks.
- CALL `memory_ingest` WHEN learning new project facts, preferences, or decisions to persist them.
- CALL `memory_feedback` AFTER executing runbooks to reinforce successful memories or trigger auto-repair on failure.
""",
)


@mcp.custom_route("/health", methods=["GET"])
async def mcp_health_check(request: Request) -> JSONResponse:
    """Lightweight liveness probe for container orchestrators."""
    return JSONResponse({"status": "ok", "engine": "strata-memory", "version": "0.1.0"})


@mcp.custom_route("/ready", methods=["GET"])
async def mcp_readiness_check(request: Request) -> JSONResponse:
    """Readiness probe verifying PostgreSQL connectivity and Ollama embedding model availability."""
    checks: Dict[str, Any] = {"postgres": "unknown", "embedding_service": "unknown"}
    ready = True

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1;")
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {exc}"
        ready = False

    embed_root = settings.embedding_base_url.rstrip("/")
    if embed_root.endswith("/v1"):
        embed_root = embed_root[:-3]
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            if settings.embedding_provider == "ollama":
                r = await client.get(f"{embed_root}/api/tags")
                r.raise_for_status()
                models = [m.get("name", "") for m in r.json().get("models", [])]
                embed_base = settings.embedding_model_name.split(":")[0]
                has_embed = any(m == settings.embedding_model_name or m.startswith(f"{embed_base}:") for m in models)
                checks["embedding_service"] = "ok" if has_embed else f"missing_model:{settings.embedding_model_name}"
                checks["loaded_models"] = models
                if not has_embed:
                    ready = False
            else:
                r = await client.get(f"{settings.embedding_base_url.rstrip('/')}/models")
                checks["embedding_service"] = "ok" if r.status_code < 400 else f"status:{r.status_code}"
    except Exception as exc:
        checks["embedding_service"] = f"error: {exc}"
        ready = False

    return JSONResponse(
        {"status": "ready" if ready else "degraded", "checks": checks},
        status_code=200 if ready else 503,
    )


# ============================================================================
# TOOL 1: memory_recall
# ============================================================================
@mcp.tool()
async def memory_recall(
    query: Annotated[
        str,
        Field(
            description=(
                "Natural language search query expressing what information, facts, runbooks, "
                "or entity relationships you need to retrieve (e.g., 'What database and region are used?')."
            )
        ),
    ],
    namespace: Annotated[
        str,
        Field(
            default="default",
            description=(
                "Multi-tenancy isolation namespace. Defaults to 'default'. Use the same namespace "
                "used when storing memories to retrieve matching records."
            ),
        ),
    ] = "default",
    pillars: Annotated[
        Optional[List[Literal["semantic", "episodic", "procedural", "entity"]]],
        Field(
            default=None,
            description=(
                "List of memory pillars to search. Defaults to all 4 pillars: "
                "['semantic', 'episodic', 'procedural', 'entity']. Specify a subset to narrow results."
            ),
        ),
    ] = None,
    top_k: Annotated[
        int,
        Field(
            default=5,
            ge=1,
            le=25,
            description="Maximum number of candidate memories to return per pillar (default: 5).",
        ),
    ] = 5,
    token_budget: Annotated[
        int,
        Field(
            default=1500,
            ge=100,
            le=8000,
            description=(
                "Maximum token budget for the returned XML context block (default: 1500). "
                "The engine dynamically packs the highest-scoring memories and safely closes XML tags."
            ),
        ),
    ] = 1500,
) -> str:
    """Retrieve relevant memories across the 4 Cognitive Memory Pillars (<15ms, Zero-LLM).

    WHEN TO USE:
    - At the start of a user session or conversation to load context and preferences.
    - Before answering technical questions, designing architecture, or modifying code.
    - Before executing a multi-step task to look up existing procedural skills and runbooks.

    HOW TO USE:
    - Pass a natural language `query` describing what you need.
    - The tool computes an Ollama embedding (nomic-embed-text, 768d), performs Reciprocal Rank
      Fusion (HNSW vector + BM25 text) on Neon, ranks procedures via Bayesian formula, and
      traverses the active entity graph.
    - Only ACTIVE facts (valid_until IS NULL) are returned; superseded facts are omitted.

    RETURNS:
    - A well-formed XML context block (`<strata_memory_context>`) ready to inject into your prompt,
      guaranteed to fit within your specified `token_budget`.
    """
    try:
        search_pillars = pillars if pillars is not None else ["semantic", "episodic", "procedural", "entity"]
        res = await svc_memory_recall(
            query=query,
            namespace=namespace,
            pillars=search_pillars,
            top_k=top_k,
            token_budget=token_budget,
        )
        return res.formatted_context
    finally:
        await maybe_suspend_neon_compute()


# ============================================================================
# TOOL 2: memory_ingest
# ============================================================================
@mcp.tool()
async def memory_ingest(
    raw_text: Annotated[
        str,
        Field(
            description=(
                "Unstructured text containing facts, user preferences, events, skills, or entity relations. "
                "Pass natural language directly without manual JSON formatting."
            )
        ),
    ],
    namespace: Annotated[
        str,
        Field(
            default="default",
            description="Target namespace partition for multi-tenancy isolation (default: 'default').",
        ),
    ] = "default",
    fast_mode: Annotated[
        bool,
        Field(
            default=False,
            description=(
                "If True, bypasses Small LLM extraction and performs immediate deterministic insertion "
                "into the semantic pillar (<15ms latency). If False (default), uses Ollama (qwen3:8b) "
                "to autonomously route facts, extract graph triples, and supersede contradictions."
            ),
        ),
    ] = False,
    source_id: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Optional external audit reference ID (e.g. git commit hash, session ID, ticket number).",
        ),
    ] = None,
    ttl_seconds: Annotated[
        Optional[int],
        Field(
            default=None,
            description="Optional time-to-live in seconds. After this duration, the memory soft-expires.",
        ),
    ] = None,
    laya_mode: Annotated[
        Optional[Literal["hybrid", "in_memory", "ollama_model", "disabled"]],
        Field(
            default=None,
            description="Optional runtime control for Laya Decision Engine mode ('hybrid', 'in_memory', 'ollama_model', 'disabled').",
        ),
    ] = None,
) -> str:
    """Autonomously ingest and route unstructured information across the 4 Memory Pillars.

    WHEN TO USE:
    - When the user shares new project decisions, architecture choices, credentials, or preferences.
    - When an event occurs that updates or contradicts previous project knowledge.
    - When you want Strata to automatically figure out whether the input is a fact, an event,
      a reusable procedure, or a relationship between entities.

    HOW TO USE:
    - Pass the raw conversation snippet or statement in `raw_text`.
    - Strata's internal Small LLM (qwen3:8b) pre-fetches similar existing memories, checks for
      contradictions, marks outdated records as superseded (valid_until = NOW()), and inserts
      new structured records across the 4 pillars.

    RETURNS:
    - JSON summary containing created IDs, superseded IDs, and counts per pillar.
    """
    try:
        res = await svc_memory_ingest(
            raw_text=raw_text,
            namespace=namespace,
            fast_mode=fast_mode,
            source_id=source_id,
            ttl_seconds=ttl_seconds,
            laya_mode=laya_mode,
        )
        return res.model_dump_json(indent=2)
    finally:
        await maybe_suspend_neon_compute()


# ============================================================================
# TOOL 3: memory_store_explicit
# ============================================================================
@mcp.tool()
async def memory_store_explicit(
    pillar: Annotated[
        Literal["semantic", "episodic", "procedural", "entity"],
        Field(
            description=(
                "Target pillar to write to: "
                "'semantic' (atomic facts), 'episodic' (event traces), "
                "'procedural' (versioned runbooks), or 'entity' (graph nodes & edges)."
            )
        ),
    ],
    payload: Annotated[
        Dict[str, Any],
        Field(
            description=(
                "Structured dictionary matching the target pillar schema: "
                "• semantic: {'summary': str, 'tags': list[str], 'confidence': float} "
                "• episodic: {'summary': str, 'situation': str, 'action_taken': str, 'outcome': str, 'success': bool} "
                "• procedural: {'name': str, 'description': str, 'trigger_condition': str, 'steps': list[str]} "
                "• entity: {'source_name': str, 'source_type': str, 'relation_type': str, 'target_name': str, 'target_type': str, 'fact_summary': str}"
            )
        ),
    ],
    namespace: Annotated[
        str,
        Field(
            default="default",
            description="Multi-tenancy isolation namespace (default: 'default').",
        ),
    ] = "default",
    ttl_seconds: Annotated[
        Optional[int],
        Field(
            default=None,
            description="Optional time-to-live in seconds. After this duration, the memory soft-expires.",
        ),
    ] = None,
    laya_mode: Annotated[
        Optional[Literal["hybrid", "in_memory", "ollama_model", "disabled"]],
        Field(
            default=None,
            description="Optional runtime control for Laya Decision Engine mode ('hybrid', 'in_memory', 'ollama_model', 'disabled').",
        ),
    ] = None,
) -> str:
    """Direct, Zero-LLM structured insertion into a specific Memory Pillar (<10ms).

    WHEN TO USE:
    - When you already know the exact pillar and have structured the memory data.
    - When logging an explicit task outcome (episodic) or registering a formal runbook (procedural).
    - When you want guaranteed zero-LLM latency without extraction overhead.

    HOW TO USE:
    - Specify the target `pillar` and supply the required schema in `payload`.
    """
    try:
        res = await svc_memory_store_explicit(
            pillar=pillar,
            payload=payload,
            namespace=namespace,
            ttl_seconds=ttl_seconds,
        )
        return json.dumps(res, indent=2)
    finally:
        await maybe_suspend_neon_compute()


# ============================================================================
# TOOL 4: memory_edit
# ============================================================================
@mcp.tool()
async def memory_edit(
    target_id_or_name: Annotated[
        str,
        Field(
            default="",
            description="UUID of the memory item, or search phrase/topic to auto-locate it, or name of the procedure/entity. Leave empty to auto-locate from instruction.",
        ),
    ] = "",
    instruction: Annotated[
        str,
        Field(
            description="Natural language instruction describing the exact modification (e.g., 'Update region to ap-southeast-1' or 'Changed role to SRE')."
        ),
    ] = "",
    pillar: Annotated[
        Literal["semantic", "procedural", "entity"],
        Field(
            default="semantic",
            description="Pillar of the target memory: 'semantic' (default), 'procedural', or 'entity'.",
        ),
    ] = "semantic",
    namespace: Annotated[
        str,
        Field(
            default="default",
            description="Multi-tenancy isolation namespace (default: 'default').",
        ),
    ] = "default",
) -> str:
    """Modify or supersede an existing memory item using natural language instructions.

    WHEN TO USE:
    - When you need to correct, update, or revise an existing fact, procedure, or entity property.
    - For semantic memories, this preserves bi-temporal history: marks the old record as superseded
      (valid_until = NOW()) and inserts the newly edited fact.
    - For procedures, this modifies steps and increments version (v1 -> v2) with an audit entry.
    """
    try:
        res = await svc_memory_edit(
            target_id_or_name=target_id_or_name,
            instruction=instruction,
            pillar=pillar,
            namespace=namespace,
        )
        return json.dumps(res, indent=2)
    finally:
        await maybe_suspend_neon_compute()


# ============================================================================
# TOOL 5: memory_feedback
# ============================================================================
@mcp.tool()
async def memory_feedback(
    memory_ids_used: Annotated[
        Optional[List[str]],
        Field(
            default=None,
            description="List of memory UUIDs that assisted the agent during task execution.",
        ),
    ] = None,
    procedure_name: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Name of the procedural skill or runbook executed by the agent.",
        ),
    ] = None,
    success: Annotated[
        bool,
        Field(
            default=True,
            description="Whether the task execution was successful (True) or failed (False).",
        ),
    ] = True,
    failure_reason: Annotated[
        Optional[str],
        Field(
            default=None,
            description=(
                "If success=False, provide the error trace or explanation of failure. "
                "Strata's Small LLM will analyze this error and automatically patch the procedure steps."
            ),
        ),
    ] = None,
    memory_query: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Optional search query or memory topic to auto-locate target memory if UUID is not known.",
        ),
    ] = None,
    namespace: Annotated[
        str,
        Field(
            default="default",
            description="Multi-tenancy isolation namespace (default: 'default').",
        ),
    ] = "default",
) -> str:
    """Report task execution feedback to adjust utility scores and auto-heal failed runbooks.

    WHEN TO USE:
    - Immediately after completing a task that utilized memories from `memory_recall`.
    - When a procedural workflow or runbook failed in production due to an error.

    HOW IT WORKS:
    - Reinforcement Loop: Successful tasks bump utility_score (+1) on memories used. Failed tasks
      penalize utility_score (-2). High-utility memories rank higher in future recall queries.
    - Self-Healing Runbooks: If `success=False` and `failure_reason` is provided, Strata analyzes
      why the procedure failed, automatically patches `steps[]`, increments the procedure `version`,
      and logs the repair explanation to `changelog`.
    """
    try:
        res = await svc_memory_feedback(
            memory_ids_used=memory_ids_used,
            procedure_name=procedure_name,
            success=success,
            failure_reason=failure_reason,
            namespace=namespace,
            memory_query=memory_query,
        )
        return json.dumps(res, indent=2)
    finally:
        await maybe_suspend_neon_compute()


# ============================================================================
# TOOL 6: memory_delete
# ============================================================================
@mcp.tool()
async def memory_delete(
    target_id: Annotated[
        str,
        Field(
            description="UUID of the memory item to delete, or name of the procedure/entity."
        ),
    ],
    pillar: Annotated[
        Literal["semantic", "episodic", "procedural", "entity"],
        Field(
            default="semantic",
            description="Pillar of the target memory: 'semantic' (default), 'episodic', 'procedural', or 'entity'.",
        ),
    ] = "semantic",
    hard_delete: Annotated[
        bool,
        Field(
            default=False,
            description=(
                "If False (default), performs a soft delete (valid_until = NOW() or is_active = FALSE), "
                "retaining an audit trail while removing from recall. If True, permanently purges the row."
            ),
        ),
    ] = False,
    namespace: Annotated[
        str,
        Field(
            default="default",
            description="Multi-tenancy isolation namespace (default: 'default').",
        ),
    ] = "default",
) -> str:
    """Soft-inactivate or permanently delete a memory record.

    WHEN TO USE:
    - To prune obsolete or incorrect memories.
    - By default (hard_delete=False), marks valid_until = NOW() to preserve historical audit trails
      while ensuring the record is never returned in future recall operations.
    """
    try:
        res = await svc_memory_delete(
            target_id=target_id,
            pillar=pillar,
            hard_delete=hard_delete,
            namespace=namespace,
        )
        return json.dumps(res, indent=2)
    finally:
        await maybe_suspend_neon_compute()


# ============================================================================
# TOOL 7: memory_prune
# ============================================================================
@mcp.tool()
async def memory_prune(
    namespace: Annotated[
        str,
        Field(
            default="default",
            description="Multi-tenancy isolation namespace to prune.",
        ),
    ] = "default",
    distill_episodes: Annotated[
        bool,
        Field(
            default=True,
            description="If True, uses Small LLM to distill reusable runbooks and permanent facts before purging raw episodes.",
        ),
    ] = True,
    episodic_older_than_days: Annotated[
        Optional[int],
        Field(
            default=30,
            description="Prune episodic memories older than X days (or those whose TTL has expired). Set None to only prune TTL-expired.",
        ),
    ] = 30,
    superseded_older_than_days: Annotated[
        int,
        Field(
            default=90,
            description="Permanently delete historical superseded/soft-deleted rows older than X days.",
        ),
    ] = 90,
    retire_toxic_threshold: Annotated[
        Optional[int],
        Field(
            default=-5,
            description="Automatically soft-retire memories with utility_score <= threshold (default: -5).",
        ),
    ] = -5,
    batch_size: Annotated[
        int,
        Field(
            default=20,
            description="Maximum number of expired episodes to distill and prune per invocation.",
        ),
    ] = 20,
) -> str:
    """Consolidates and prunes expired or stale memories using Cognitive Distillation.

    WHEN TO USE:
    - Periodically to reclaim storage and keep retrieval fast.
    - To safely retire old episodic logs without losing hard-won lessons (synthesizes them into runbooks & semantic facts).
    - To purge dead superseded facts and auto-retire toxic memories that repeatedly cause failures.
    """
    try:
        res = await svc_memory_prune(
            namespace=namespace,
            distill_episodes=distill_episodes,
            episodic_older_than_days=episodic_older_than_days,
            superseded_older_than_days=superseded_older_than_days,
            retire_toxic_threshold=retire_toxic_threshold,
            batch_size=batch_size,
        )
        return res.model_dump_json(indent=2)
    finally:
        await maybe_suspend_neon_compute()


# ============================================================================
# TOOL 8: memory_purge_namespace
# ============================================================================
@mcp.tool()
async def memory_purge_namespace(
    namespace: Annotated[
        str,
        Field(
            description="Name of the namespace to completely erase.",
        ),
    ],
    confirm: Annotated[
        bool,
        Field(
            default=False,
            description="Explicit confirmation flag (must be True to execute destructive wipe).",
        ),
    ] = False,
) -> str:
    """Permanently purges all memories, procedures, and entity nodes/edges in a namespace.

    WHEN TO USE:
    - User privacy / GDPR Right to be Forgotten requests.
    - Resetting temporary test or staging namespaces.
    """
    try:
        res = await svc_memory_purge_namespace(
            namespace=namespace,
            confirm=confirm,
        )
        return res.model_dump_json(indent=2)
    finally:
        await maybe_suspend_neon_compute()


# ============================================================================
# TOOL 9: working_memory_record_tool_output
# ============================================================================
@mcp.tool()
def working_memory_record_tool_output(
    session_id: Annotated[
        str,
        Field(description="Active session or trajectory ID."),
    ],
    tool_call_id: Annotated[
        str,
        Field(description="Unique ID of the tool call (e.g. call_abc123)."),
    ],
    tool_name: Annotated[
        str,
        Field(description="Name of the tool that was executed."),
    ],
    content: Annotated[
        str,
        Field(description="Tool output / execution results."),
    ],
    namespace: Annotated[
        str,
        Field(default="default", description="Namespace partition (default: 'default')."),
    ] = "default",
    protected: Annotated[
        bool,
        Field(
            default=True,
            description="Whether this result is pinned against budget eviction (default: True to prevent Eviction Policy Bug).",
        ),
    ] = True,
) -> str:
    """Record an active tool output into short-term working context buffer, pinned against eviction.

    WHEN TO USE:
    - Immediately after executing a tool whose result is needed for downstream steps.
    - Prevents the Eviction Policy Bug where active tool output is evicted and causes repeated tool retries.
    """
    res = svc_working_memory_add_tool_output(
        namespace=namespace,
        session_id=session_id,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        content=content,
        protected=protected,
    )
    return json.dumps(res, indent=2)


# ============================================================================
# TOOL 10: working_memory_unprotect
# ============================================================================
@mcp.tool()
def working_memory_unprotect(
    session_id: Annotated[
        str,
        Field(description="Active session or trajectory ID."),
    ],
    tool_call_id: Annotated[
        str,
        Field(description="Unique ID of the tool call to unprotect."),
    ],
    namespace: Annotated[
        str,
        Field(default="default", description="Namespace partition (default: 'default')."),
    ] = "default",
) -> str:
    """Unprotects a previously pinned tool output once dependent steps have completed."""
    unprotected = svc_working_memory_unprotect(
        namespace=namespace,
        session_id=session_id,
        tool_call_id=tool_call_id,
    )
    return json.dumps({"session_id": session_id, "tool_call_id": tool_call_id, "unprotected": unprotected}, indent=2)


# ============================================================================
# TOOL 11: working_memory_get_context
# ============================================================================
@mcp.tool()
def working_memory_get_context(
    session_id: Annotated[
        str,
        Field(description="Active session or trajectory ID."),
    ],
    namespace: Annotated[
        str,
        Field(default="default", description="Namespace partition (default: 'default')."),
    ] = "default",
    max_tokens: Annotated[
        Optional[int],
        Field(
            default=None,
            description="Optional token budget limit. Evicts oldest non-protected items first; protected items are NEVER evicted.",
        ),
    ] = None,
) -> str:
    """Retrieves current short-term working context items for a session."""
    res = svc_working_memory_get(
        namespace=namespace,
        session_id=session_id,
        max_tokens=max_tokens,
    )
    return json.dumps(res, indent=2)


def main() -> None:
    """Entry point for FastMCP server."""
    parser = argparse.ArgumentParser(description="Strata FastMCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http", "http"],
        default=settings.mcp_transport,
        help="FastMCP transport mode: stdio, sse, streamable-http, or http (default from MCP_TRANSPORT or stdio)",
    )
    parser.add_argument(
        "--host",
        default=settings.mcp_host,
        help="Host for HTTP/SSE transport (default from MCP_HOST or 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.mcp_port,
        help="Port for HTTP/SSE transport (default from MCP_PORT or 8000)",
    )
    parser.add_argument(
        "--path",
        default=settings.mcp_path,
        help="HTTP endpoint path for streamable-http/http transport (default from MCP_PATH or /mcp)",
    )
    parser.add_argument(
        "--stateful",
        action="store_true",
        help="Disable stateless HTTP mode and preserve per-client in-memory MCP sessions",
    )
    args = parser.parse_args()

    if args.transport in ("sse", "streamable-http", "http"):
        http_middleware = (
            [Middleware(BearerAuthMiddleware, token=settings.mcp_auth_token)]
            if settings.mcp_auth_token
            else None
        )
        run_kwargs: Dict[str, Any] = {
            "transport": args.transport,
            "host": args.host,
            "port": args.port,
            "middleware": http_middleware,
        }
        if args.transport in ("streamable-http", "http"):
            run_kwargs["path"] = args.path
            run_kwargs["stateless_http"] = False if args.stateful else settings.mcp_stateless_http

        logger.info(
            f"Starting Strata MCP server (transport={args.transport}, host={args.host}, "
            f"port={args.port}, path={args.path}, auth={'enabled' if settings.mcp_auth_token else 'disabled'})"
        )
        mcp.run(**run_kwargs)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
