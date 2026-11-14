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
    RecallRequest,
    RecallResponse,
    StoreExplicitRequest,
)
from strata.service import (
    svc_memory_delete,
    svc_memory_edit,
    svc_memory_feedback,
    svc_memory_ingest,
    svc_memory_recall,
    svc_memory_store_explicit,
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
    """Autonomous 4-pillar extraction & storage using Small Decision LLM."""
    try:
        return await svc_memory_ingest(
            raw_text=req.raw_text,
            namespace=req.namespace,
            fast_mode=req.fast_mode,
            source_id=req.source_id,
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


def main() -> None:
    """CLI launcher for Strata FastAPI server."""
    uvicorn.run(
        "strata.rest_api:app",
        host=settings.strata_api_host,
        port=settings.strata_api_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
