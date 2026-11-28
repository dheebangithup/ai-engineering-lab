from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional
import uvicorn
from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from strata.config import settings
from strata.db import close_db_pool, get_db_pool
from strata.neon_control import maybe_suspend_neon_compute
from strata.models import (
    DeleteRequest,
    EditRequest,
    FeedbackRequest,
    IngestRequest,
    IngestResponse,
    PruneRequest,
    PruneResponse,
    PurgeNamespaceRequest,
    PurgeNamespaceResponse,
    RecallRequest,
    RecallResponse,
    StoreExplicitRequest,
    WorkingMemoryAddRequest,
    WorkingMemoryToolOutputRequest,
    WorkingMemoryUnprotectRequest,
)
from strata.service import (
    svc_memory_delete,
    svc_memory_edit,
    svc_memory_feedback,
    svc_memory_ingest,
    svc_memory_prune,
    svc_memory_purge_namespace,
    svc_memory_recall,
    svc_memory_store_explicit,
    svc_working_memory_add,
    svc_working_memory_add_tool_output,
    svc_working_memory_clear,
    svc_working_memory_get,
    svc_working_memory_unprotect,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB connection pool
    await get_db_pool()
    yield
    # Shutdown DB pool
    await close_db_pool()
    await maybe_suspend_neon_compute()


app = FastAPI(
    title="Strata Memory Engine API",
    description="Standalone 4-Pillar Cognitive Memory Engine on Neon PostgreSQL",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def neon_compute_lifecycle_middleware(request: Request, call_next):
    """Hits the Neon suspend API at the end of every memory API call to minimize compute cost."""
    try:
        response = await call_next(request)
        return response
    finally:
        if request.url.path.startswith("/v1/memory"):
            await maybe_suspend_neon_compute()



api_router = APIRouter()


@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "ok", "engine": "strata-memory", "version": "0.1.0"}


@api_router.post("/memory/ingest", response_model=IngestResponse)
async def api_memory_ingest(req: IngestRequest) -> IngestResponse:
    """Autonomous 4-pillar extraction & storage using Laya Decision Engine and Small LLM."""
    try:
        return await svc_memory_ingest(
            raw_text=req.raw_text,
            namespace=req.namespace,
            fast_mode=req.fast_mode,
            source_id=req.source_id,
            contradiction_threshold=req.contradiction_threshold,
            use_decision_model=req.use_decision_model,
            ttl_seconds=req.ttl_seconds,
            laya_mode=req.laya_mode,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@api_router.post("/memory/recall", response_model=RecallResponse)
async def api_memory_recall(req: RecallRequest) -> RecallResponse:
    """Deterministic, zero-LLM recall across requested memory pillars (<15ms)."""
    try:
        return await svc_memory_recall(
            query=req.query,
            namespace=req.namespace,
            pillars=req.pillars,
            top_k=req.top_k,
            token_budget=req.token_budget,
            match_threshold=req.match_threshold,
            min_score=req.min_score,
            similarity_threshold=req.similarity_threshold,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@api_router.post("/memory/store")
async def api_memory_store(req: StoreExplicitRequest) -> Dict[str, Any]:
    """Direct, zero-LLM structured write to any of the 4 pillars."""
    try:
        return await svc_memory_store_explicit(
            pillar=req.pillar,
            payload=req.payload,
            namespace=req.namespace,
            ttl_seconds=req.ttl_seconds,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@api_router.post("/memory/edit")
async def api_memory_edit(req: EditRequest) -> Dict[str, Any]:
    """Uses the Memory-Side Small LLM to modify or supersede an existing memory."""
    try:
        return await svc_memory_edit(
            target_id_or_name=req.target_id_or_name,
            instruction=req.instruction,
            pillar=req.pillar,
            namespace=req.namespace,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@api_router.post("/memory/feedback")
async def api_memory_feedback(req: FeedbackRequest) -> Dict[str, Any]:
    """Updates utility scores on used memories, and auto-patches procedures on failure."""
    try:
        return await svc_memory_feedback(
            memory_ids_used=req.memory_ids_used,
            procedure_name=req.procedure_name,
            success=req.success,
            failure_reason=req.failure_reason,
            namespace=req.namespace,
            memory_query=req.memory_query,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@api_router.post("/memory/delete")
async def api_memory_delete(req: DeleteRequest) -> Dict[str, Any]:
    """Soft-invalidates or permanently deletes a memory record."""
    try:
        return await svc_memory_delete(
            target_id=req.target_id,
            pillar=req.pillar,
            hard_delete=req.hard_delete,
            namespace=req.namespace,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@api_router.post("/memory/prune", response_model=PruneResponse)
async def api_memory_prune(req: PruneRequest) -> PruneResponse:
    """Consolidates and prunes expired/stale memories via Cognitive Distillation."""
    try:
        return await svc_memory_prune(
            namespace=req.namespace,
            distill_episodes=req.distill_episodes,
            episodic_older_than_days=req.episodic_older_than_days,
            superseded_older_than_days=req.superseded_older_than_days,
            retire_toxic_threshold=req.retire_toxic_threshold,
            batch_size=req.batch_size,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@api_router.post("/memory/purge-namespace", response_model=PurgeNamespaceResponse)
async def api_memory_purge_namespace(req: PurgeNamespaceRequest) -> PurgeNamespaceResponse:
    """Permanently purges all data in a namespace (GDPR / reset compliance)."""
    try:
        return await svc_memory_purge_namespace(
            namespace=req.namespace,
            confirm=req.confirm,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================================
# WORKING MEMORY ENDPOINTS (SHORT-TERM CONTEXT BUFFER)
# ============================================================================

@api_router.post("/working-memory/message")
async def api_working_memory_add(req: WorkingMemoryAddRequest) -> Dict[str, Any]:
    """Appends an active message to the working context buffer."""
    return svc_working_memory_add(
        namespace=req.namespace,
        session_id=req.session_id,
        role=req.role,
        content=req.content,
        turn_id=req.turn_id,
        tool_call_id=req.tool_call_id,
        tool_name=req.tool_name,
        is_tool_output=req.is_tool_output,
        protected=req.protected,
        metadata=req.metadata,
    )


@api_router.post("/working-memory/tool-output")
async def api_working_memory_tool_output(req: WorkingMemoryToolOutputRequest) -> Dict[str, Any]:
    """Records a tool output pinned as protected=True by default."""
    return svc_working_memory_add_tool_output(
        namespace=req.namespace,
        session_id=req.session_id,
        tool_call_id=req.tool_call_id,
        tool_name=req.tool_name,
        content=req.content,
        protected=req.protected,
        metadata=req.metadata,
    )


@api_router.post("/working-memory/unprotect")
async def api_working_memory_unprotect(req: WorkingMemoryUnprotectRequest) -> Dict[str, Any]:
    """Unprotects a tool result once downstream dependent reasoning completes."""
    unprotected = svc_working_memory_unprotect(
        namespace=req.namespace,
        session_id=req.session_id,
        tool_call_id=req.tool_call_id,
    )
    return {"unprotected": unprotected}


@api_router.get("/working-memory/{namespace}/{session_id}")
async def api_working_memory_get(
    namespace: str,
    session_id: str,
    max_tokens: int = None,
) -> Dict[str, Any]:
    """Retrieves active working memory items, enforcing budget without evicting protected items."""
    return svc_working_memory_get(
        namespace=namespace,
        session_id=session_id,
        max_tokens=max_tokens,
    )


@api_router.delete("/working-memory/{namespace}/{session_id}")
async def api_working_memory_clear(namespace: str, session_id: str) -> Dict[str, Any]:
    """Clears working memory for a session."""
    cleared = svc_working_memory_clear(namespace, session_id)
    return {"cleared_count": cleared}


# ============================================================================
# UI VISUALIZER & INSPECTION ENDPOINTS
# ============================================================================

@api_router.get("/ui/stats")
async def api_ui_stats(namespace: Optional[str] = None) -> Dict[str, Any]:
    """Summary counts for the 4 pillars, active vs superseded, and available namespaces."""
    pool = await get_db_pool()
    async with pool.acquire() as c:
        ns_rows = await c.fetch(
            """
            SELECT DISTINCT namespace FROM memories
            UNION
            SELECT DISTINCT namespace FROM procedural_memories
            UNION
            SELECT DISTINCT namespace FROM entity_nodes
            ORDER BY namespace ASC;
            """
        )
        namespaces = [r["namespace"] for r in ns_rows] if ns_rows else ["default"]
        if "default" not in namespaces:
            namespaces.insert(0, "default")

        ns_filter = "WHERE namespace = $1" if namespace else ""
        args = [namespace] if namespace else []

        mem_rows = await c.fetch(
            f"""
            SELECT 
                type,
                COUNT(*) FILTER (WHERE valid_until IS NULL OR valid_until > NOW()) as active_count,
                COUNT(*) FILTER (WHERE valid_until IS NOT NULL AND valid_until <= NOW()) as superseded_count,
                COUNT(*) as total_count
            FROM memories
            {ns_filter}
            GROUP BY type;
            """,
            *args,
        )

        proc_row = await c.fetchrow(
            f"SELECT COUNT(*) as count FROM procedural_memories {ns_filter};",
            *args,
        )

        ent_node_row = await c.fetchrow(
            f"SELECT COUNT(*) as count FROM entity_nodes {ns_filter};",
            *args,
        )

        ent_edge_row = await c.fetchrow(
            f"""
            SELECT 
                COUNT(*) FILTER (WHERE valid_until IS NULL OR valid_until > NOW()) as active_count,
                COUNT(*) FILTER (WHERE valid_until IS NOT NULL AND valid_until <= NOW()) as invalidated_count,
                COUNT(*) as total_count
            FROM entity_edges
            {ns_filter};
            """,
            *args,
        )

        semantic_data = next((r for r in mem_rows if r["type"] == "semantic"), None)
        episodic_data = next((r for r in mem_rows if r["type"] == "episodic"), None)

        return {
            "namespaces": namespaces,
            "semantic": {
                "active": semantic_data["active_count"] if semantic_data else 0,
                "superseded": semantic_data["superseded_count"] if semantic_data else 0,
                "total": semantic_data["total_count"] if semantic_data else 0,
            },
            "episodic": {
                "active": episodic_data["active_count"] if episodic_data else 0,
                "superseded": episodic_data["superseded_count"] if episodic_data else 0,
                "total": episodic_data["total_count"] if episodic_data else 0,
            },
            "procedural": {
                "count": proc_row["count"] if proc_row else 0,
            },
            "entity_nodes": {
                "count": ent_node_row["count"] if ent_node_row else 0,
            },
            "entity_edges": {
                "active": ent_edge_row["active_count"] if ent_edge_row else 0,
                "invalidated": ent_edge_row["invalidated_count"] if ent_edge_row else 0,
                "total": ent_edge_row["total_count"] if ent_edge_row else 0,
            },
        }


@api_router.get("/ui/memories")
async def api_ui_memories(
    namespace: str = "default",
    pillar: Optional[str] = None,
    status: Optional[str] = "all",
    search: Optional[str] = None,
    time_range: Optional[str] = "30d",
    page: int = 1,
    page_size: int = 25,
) -> Dict[str, Any]:
    """Paginated memory inspection with full-text search, date-windowing, and status filters."""
    pool = await get_db_pool()
    conditions = ["namespace = $1"]
    args: List[Any] = [namespace]

    if pillar and pillar in ("semantic", "episodic"):
        args.append(pillar)
        conditions.append(f"type = ${len(args)}")

    if status == "active":
        conditions.append("(valid_until IS NULL OR valid_until > NOW())")
    elif status == "superseded":
        conditions.append("(valid_until IS NOT NULL AND valid_until <= NOW())")

    # Time-range windowing
    if time_range == "24h":
        conditions.append("created_at >= NOW() - INTERVAL '24 hours'")
    elif time_range == "7d":
        conditions.append("created_at >= NOW() - INTERVAL '7 days'")
    elif time_range == "30d":
        conditions.append("created_at >= NOW() - INTERVAL '30 days'")
    elif time_range == "90d":
        conditions.append("created_at >= NOW() - INTERVAL '90 days'")

    # Full-text / substring search
    if search and search.strip():
        clean_search = search.strip()
        args.append(clean_search)
        search_idx = len(args)
        conditions.append(
            f"(to_tsvector('english', summary) @@ plainto_tsquery('english', ${search_idx}) OR summary ILIKE ('%' || ${search_idx} || '%'))"
        )

    where_clause = " AND ".join(conditions)

    # Safe pagination bounds
    page = max(1, page)
    page_size = max(5, min(100, page_size))
    offset = (page - 1) * page_size

    async with pool.acquire() as c:
        count_row = await c.fetchrow(f"SELECT COUNT(*) as count FROM memories WHERE {where_clause}", *args)
        total = count_row["count"] if count_row else 0
        total_pages = max(1, (total + page_size - 1) // page_size) if total > 0 else 1

        args.extend([page_size, offset])
        sql = f"""
            SELECT 
                memory_id, namespace, type, summary, payload, tags,
                confidence, utility_score, access_count, source_id,
                superseded_by, valid_from, valid_until, reaffirmed_at, created_at,
                CASE WHEN (valid_until IS NULL OR valid_until > NOW()) THEN TRUE ELSE FALSE END as is_active
            FROM memories
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ${len(args) - 1} OFFSET ${len(args)};
        """
        rows = await c.fetch(sql, *args)

        items = []
        for r in rows:
            items.append({
                "memory_id": str(r["memory_id"]),
                "namespace": r["namespace"],
                "type": r["type"],
                "summary": r["summary"],
                "payload": r["payload"],
                "tags": r["tags"],
                "confidence": r["confidence"],
                "utility_score": r["utility_score"],
                "access_count": r["access_count"],
                "source_id": r["source_id"],
                "superseded_by": str(r["superseded_by"]) if r["superseded_by"] else None,
                "valid_from": r["valid_from"].isoformat() if r["valid_from"] else None,
                "valid_until": r["valid_until"].isoformat() if r["valid_until"] else None,
                "reaffirmed_at": r["reaffirmed_at"].isoformat() if r["reaffirmed_at"] else None,
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "is_active": r["is_active"],
            })

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "items": items,
        }


@api_router.get("/ui/graph")
async def api_ui_graph(
    namespace: str = "default",
    include_invalidated: bool = True,
    search: Optional[str] = None,
    time_range: Optional[str] = "30d",
    center_entity_id: Optional[str] = None,
    limit: int = 60,
) -> Dict[str, Any]:
    """Retrieves entity nodes and relationships bounded by search, 1-hop focus, and limit."""
    pool = await get_db_pool()
    safe_limit = max(10, min(200, limit))

    async with pool.acquire() as c:
        if center_entity_id:
            # 1-Hop Ego-Centric sub-graph expansion from a selected center node
            nodes_rows = await c.fetch(
                """
                WITH focal_edges AS (
                    SELECT source_entity_id, target_entity_id
                    FROM entity_edges
                    WHERE namespace = $1 
                      AND (source_entity_id = $2::uuid OR target_entity_id = $2::uuid)
                      AND ($3::bool OR valid_until IS NULL OR valid_until > NOW())
                    LIMIT $4
                ),
                focal_node_ids AS (
                    SELECT $2::uuid as entity_id
                    UNION
                    SELECT source_entity_id FROM focal_edges
                    UNION
                    SELECT target_entity_id FROM focal_edges
                )
                SELECT n.entity_id, n.name, n.entity_type, n.summary, n.attributes, n.is_active, n.updated_at
                FROM entity_nodes n
                INNER JOIN focal_node_ids fn ON n.entity_id = fn.entity_id
                WHERE n.namespace = $1;
                """,
                namespace,
                center_entity_id,
                include_invalidated,
                safe_limit,
            )

            edge_sql = """
                SELECT edge_id, source_entity_id, relation_type, target_entity_id, fact_summary, properties, valid_from, valid_until,
                       CASE WHEN (valid_until IS NULL OR valid_until > NOW()) THEN TRUE ELSE FALSE END as is_active
                FROM entity_edges
                WHERE namespace = $1
                  AND (source_entity_id = $2::uuid OR target_entity_id = $2::uuid)
                  AND ($3::bool OR valid_until IS NULL OR valid_until > NOW())
                LIMIT $4;
            """
            edges_rows = await c.fetch(edge_sql, namespace, center_entity_id, include_invalidated, safe_limit)

        else:
            # Standard bounded node retrieval with optional search & date filter
            node_conditions = ["namespace = $1"]
            node_args: List[Any] = [namespace]

            if search and search.strip():
                clean_search = search.strip()
                node_args.append(clean_search)
                node_conditions.append(f"(name ILIKE ('%' || ${len(node_args)} || '%') OR summary ILIKE ('%' || ${len(node_args)} || '%'))")

            if time_range == "24h":
                node_conditions.append("updated_at >= NOW() - INTERVAL '24 hours'")
            elif time_range == "7d":
                node_conditions.append("updated_at >= NOW() - INTERVAL '7 days'")
            elif time_range == "30d":
                node_conditions.append("updated_at >= NOW() - INTERVAL '30 days'")
            elif time_range == "90d":
                node_conditions.append("updated_at >= NOW() - INTERVAL '90 days'")

            node_args.append(safe_limit)
            nodes_rows = await c.fetch(
                f"""
                SELECT entity_id, name, entity_type, summary, attributes, is_active, updated_at
                FROM entity_nodes
                WHERE {" AND ".join(node_conditions)}
                ORDER BY updated_at DESC
                LIMIT ${len(node_args)};
                """,
                *node_args,
            )

            retrieved_node_ids = [r["entity_id"] for r in nodes_rows]
            if retrieved_node_ids:
                edge_conditions = [
                    "namespace = $1",
                    "(source_entity_id = ANY($2::uuid[]) OR target_entity_id = ANY($2::uuid[]))",
                ]
                if not include_invalidated:
                    edge_conditions.append("(valid_until IS NULL OR valid_until > NOW())")

                edges_rows = await c.fetch(
                    f"""
                    SELECT edge_id, source_entity_id, relation_type, target_entity_id, fact_summary, properties, valid_from, valid_until,
                           CASE WHEN (valid_until IS NULL OR valid_until > NOW()) THEN TRUE ELSE FALSE END as is_active
                    FROM entity_edges
                    WHERE {" AND ".join(edge_conditions)}
                    LIMIT {safe_limit * 2};
                    """,
                    namespace,
                    retrieved_node_ids,
                )
            else:
                edges_rows = []

        nodes = [
            {
                "id": str(r["entity_id"]),
                "name": r["name"],
                "entity_type": r["entity_type"],
                "summary": r["summary"],
                "attributes": r["attributes"],
                "is_active": r["is_active"],
            }
            for r in nodes_rows
        ]

        edges = [
            {
                "id": str(r["edge_id"]),
                "source": str(r["source_entity_id"]),
                "target": str(r["target_entity_id"]),
                "relation": r["relation_type"],
                "fact": r["fact_summary"],
                "properties": r["properties"],
                "is_active": r["is_active"],
                "valid_from": r["valid_from"].isoformat() if r["valid_from"] else None,
                "valid_until": r["valid_until"].isoformat() if r["valid_until"] else None,
            }
            for r in edges_rows
        ]

        return {"nodes": nodes, "edges": edges, "limit": safe_limit}


@api_router.get("/ui/lineage/{memory_id}")
async def api_ui_lineage(memory_id: str, namespace: str = "default") -> Dict[str, Any]:
    """Traces full superseding revision history forward and backward for a memory."""
    pool = await get_db_pool()
    async with pool.acquire() as c:
        # Recursive CTE to find entire chain
        sql = """
        WITH RECURSIVE forward_chain AS (
            SELECT memory_id, summary, tags, superseded_by, valid_from, valid_until, utility_score, confidence, created_at, 0 as depth
            FROM memories
            WHERE memory_id = $1::uuid AND namespace = $2
            UNION ALL
            SELECT m.memory_id, m.summary, m.tags, m.superseded_by, m.valid_from, m.valid_until, m.utility_score, m.confidence, m.created_at, fc.depth + 1
            FROM memories m
            INNER JOIN forward_chain fc ON m.memory_id = fc.superseded_by
        ),
        backward_chain AS (
            SELECT memory_id, summary, tags, superseded_by, valid_from, valid_until, utility_score, confidence, created_at, -1 as depth
            FROM memories
            WHERE superseded_by = $1::uuid AND namespace = $2
            UNION ALL
            SELECT m.memory_id, m.summary, m.tags, m.superseded_by, m.valid_from, m.valid_until, m.utility_score, m.confidence, m.created_at, bc.depth - 1
            FROM memories m
            INNER JOIN backward_chain bc ON m.superseded_by = bc.memory_id
        )
        SELECT * FROM forward_chain
        UNION
        SELECT * FROM backward_chain
        ORDER BY created_at ASC;
        """
        rows = await c.fetch(sql, memory_id, namespace)
        chain = [
            {
                "memory_id": str(r["memory_id"]),
                "summary": r["summary"],
                "tags": r["tags"],
                "superseded_by": str(r["superseded_by"]) if r["superseded_by"] else None,
                "valid_from": r["valid_from"].isoformat() if r["valid_from"] else None,
                "valid_until": r["valid_until"].isoformat() if r["valid_until"] else None,
                "is_active": r["valid_until"] is None or r["valid_until"] > r["created_at"],
                "utility_score": r["utility_score"],
                "confidence": r["confidence"],
                "created_at": r["created_at"].isoformat(),
            }
            for r in rows
        ]
        return {"memory_id": memory_id, "chain": chain}


@api_router.get("/ui/procedures")
async def api_ui_procedures(namespace: str = "default") -> List[Dict[str, Any]]:
    """Lists all procedural runbooks with execution histories, changelogs, and Bayesian success rates."""
    pool = await get_db_pool()
    async with pool.acquire() as c:
        rows = await c.fetch(
            """
            SELECT 
                procedure_id, name, description, trigger_condition, steps, prerequisites,
                version, changelog, success_count, fail_count, is_active, updated_at,
                ((success_count + 1)::float / (success_count + fail_count + 2)::float) AS success_rate
            FROM procedural_memories
            WHERE namespace = $1
            ORDER BY updated_at DESC;
            """,
            namespace,
        )
        return [
            {
                "procedure_id": str(r["procedure_id"]),
                "name": r["name"],
                "description": r["description"],
                "trigger_condition": r["trigger_condition"],
                "steps": r["steps"],
                "prerequisites": r["prerequisites"],
                "version": r["version"],
                "changelog": r["changelog"],
                "success_count": r["success_count"],
                "fail_count": r["fail_count"],
                "success_rate": round(float(r["success_rate"]), 4),
                "is_active": r["is_active"],
                "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
            }
            for r in rows
        ]


app.include_router(api_router, prefix="/v1")

# Mount pre-built UI static files if present
_ui_dist_path = Path(__file__).resolve().parent.parent.parent / "ui" / "dist"
if _ui_dist_path.exists():
    app.mount("/ui", StaticFiles(directory=str(_ui_dist_path), html=True), name="ui")


def main() -> None:
    """CLI launcher for Strata FastAPI server."""
    import argparse

    parser = argparse.ArgumentParser(description="Strata Memory Engine REST API")
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=settings.strata_api_port,
        help=f"Port to bind to (default: {settings.strata_api_port})",
    )
    parser.add_argument(
        "-H", "--host",
        type=str,
        default=settings.strata_api_host,
        help=f"Host to bind to (default: {settings.strata_api_host})",
    )
    args = parser.parse_args()

    uvicorn.run(
        "strata.rest_api:app",
        host=args.host,
        port=args.port,
        loop="asyncio",
        reload=False,
    )


if __name__ == "__main__":
    main()
