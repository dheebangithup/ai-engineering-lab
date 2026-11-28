from contextlib import asynccontextmanager
from typing import Any, Dict
import uvicorn
from fastapi import FastAPI, HTTPException, Request

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


@app.middleware("http")
async def neon_compute_lifecycle_middleware(request: Request, call_next):
    """Hits the Neon suspend API at the end of every memory API call to minimize compute cost."""
    try:
        response = await call_next(request)
        return response
    finally:
        if request.url.path.startswith("/v1/memory"):
            await maybe_suspend_neon_compute()



@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "ok", "engine": "strata-memory", "version": "0.1.0"}


@app.post("/v1/memory/ingest", response_model=IngestResponse)
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


@app.post("/v1/memory/recall", response_model=RecallResponse)
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


@app.post("/v1/memory/store")
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


@app.post("/v1/memory/edit")
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


@app.post("/v1/memory/feedback")
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


@app.post("/v1/memory/delete")
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


@app.post("/v1/memory/prune", response_model=PruneResponse)
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


@app.post("/v1/memory/purge-namespace", response_model=PurgeNamespaceResponse)
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

@app.post("/v1/working-memory/message")
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


@app.post("/v1/working-memory/tool-output")
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


@app.post("/v1/working-memory/unprotect")
async def api_working_memory_unprotect(req: WorkingMemoryUnprotectRequest) -> Dict[str, Any]:
    """Unprotects a tool result once downstream dependent reasoning completes."""
    unprotected = svc_working_memory_unprotect(
        namespace=req.namespace,
        session_id=req.session_id,
        tool_call_id=req.tool_call_id,
    )
    return {"unprotected": unprotected}


@app.get("/v1/working-memory/{namespace}/{session_id}")
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


@app.delete("/v1/working-memory/{namespace}/{session_id}")
async def api_working_memory_clear(namespace: str, session_id: str) -> Dict[str, Any]:
    """Clears working memory for a session."""
    cleared = svc_working_memory_clear(namespace, session_id)
    return {"cleared_count": cleared}


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
