from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from jarvis.agent import AgentExecutionResult, JarvisAgent
from jarvis.config import load_env
from jarvis.logger import LogFileName, get_logger, setup_logging
from jarvis.workspace import default_workspace, initialize_workspace

# Ensure env & workspace initialization
load_env()
initialize_workspace()
setup_logging()
logger = get_logger("ui.server")

DEFAULT_SERVER_TITLE: str = "J.A.R.V.I.S. Multi-Agent System"
DEFAULT_SERVER_VERSION: str = "1.0.0"
DEFAULT_LOG_LINES_TAIL: int = 100
INDEX_HTML_FILENAME: str = "index.html"
STATIC_MOUNT_PATH: str = "/static"
DEFAULT_ENCODING: str = "utf-8"

import time
from fastapi import Request

app = FastAPI(title=DEFAULT_SERVER_TITLE, version=DEFAULT_SERVER_VERSION)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    client_host = request.client.host if request.client else "unknown"
    method = request.method
    path = request.url.path

    logger.info(f"HTTP {method} {path} incoming from {client_host}")
    try:
        response = await call_next(request)
        process_time_ms = (time.time() - start_time) * 1000
        logger.info(f"HTTP {method} {path} -> status={response.status_code} ({process_time_ms:.1f}ms)")
        return response
    except Exception as e:
        process_time_ms = (time.time() - start_time) * 1000
        logger.error(f"HTTP {method} {path} -> error={e} ({process_time_ms:.1f}ms)", exc_info=True)
        raise

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Mount static folder
app.mount(STATIC_MOUNT_PATH, StaticFiles(directory=str(STATIC_DIR)), name="static")

# Shared Agent Singleton
_agent: Optional[JarvisAgent] = None


def get_agent() -> JarvisAgent:
    global _agent
    if _agent is None:
        _agent = JarvisAgent(
            workspace_dir=default_workspace().root,
            auto_save_results=True,
            use_supervisor=True,
        )
    return _agent


class ChatRequest(BaseModel):
    task: str
    human_response: Optional[str] = None


class ChatResponse(BaseModel):
    task: str
    success: bool
    outcome: str
    verdict: str
    trials: int
    plan: str
    worker: Optional[str] = None
    needs_human_input: bool = False
    clarification_question: Optional[str] = None
    events: List[Dict[str, Any]] = []


@app.get("/")
async def serve_index():
    index_file = STATIC_DIR / INDEX_HTML_FILENAME
    if not index_file.is_file():
        raise HTTPException(status_code=404, detail="Frontend index.html not found.")
    return FileResponse(str(index_file))


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    if not req.task.strip():
        raise HTTPException(status_code=400, detail="Task query cannot be empty.")

    logger.info(f"Incoming task request: '{req.task}' (human_response: '{req.human_response}')")
    agent = get_agent()
    try:
        res: AgentExecutionResult = agent.run(
            task=req.task,
            human_response=req.human_response,
        )

        logger.info(
            f"Agent completed task: worker={res.worker}, success={res.success}, "
            f"trials={res.trials}, verdict={res.verdict}"
        )

        return ChatResponse(
            task=res.task,
            success=res.success,
            outcome=res.outcome,
            verdict=res.verdict,
            trials=res.trials,
            plan=res.plan,
            worker=res.worker,
            needs_human_input=res.needs_human_input,
            clarification_question=res.clarification_question,
            events=res.events,
        )
    except Exception as e:
        logger.error(f"Task execution failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")


@app.get("/api/workspace")
async def workspace_endpoint():
    ws = default_workspace()
    files_info = []

    if ws.root.exists():
        for item in sorted(ws.root.iterdir()):
            if item.name.startswith("."):
                continue
            files_info.append({
                "name": item.name,
                "is_dir": item.is_dir(),
                "size": item.stat().st_size if item.is_file() else 0,
            })

    return {
        "root": str(ws.root),
        "files": files_info,
    }


@app.get("/api/logs")
async def get_logs_endpoint(lines: int = DEFAULT_LOG_LINES_TAIL):
    """Return the tail of the application logs."""
    ws = default_workspace()
    log_file = ws.logs_dir / LogFileName.APP.value
    if not log_file.exists():
        return {"logs": [], "file": str(log_file)}

    try:
        with open(log_file, "r", encoding=DEFAULT_ENCODING, errors="replace") as f:
            all_lines = f.readlines()
            tail_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        return {
            "logs": [l.rstrip("\r\n") for l in tail_lines],
            "file": str(log_file),
            "total_lines": len(all_lines),
        }
    except Exception as e:
        logger.error(f"Failed to read logs: {e}")
        return {"error": str(e), "file": str(log_file)}


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": "J.A.R.V.I.S. Multi-Agent System"}
