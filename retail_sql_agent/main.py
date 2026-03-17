"""
SQL Analyst Agent — Web UI Entry Point.
Starts the FastAPI server to host the Flow Visualizer dashboard.
"""

from dotenv import load_dotenv
load_dotenv()  # Load environment variables first!

import json
import os
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from agent.retail_agent import RetailAgent
from config import logger

class RenameRequest(BaseModel):
    title: str

app = FastAPI(title="SQL Analyst Agent API")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared agent instance
agent = RetailAgent()


@app.get("/stream")
async def stream_agent(question: str, session_id: str = None):
    logger.info(f"Received question: {question} (Session: {session_id})")
    
    # Update agent's session_id if provided
    if session_id:
        agent.session_id = session_id
    elif not agent.session_id:
        # If no session_id is active, the SDK will create one in stream_ask
        pass
    """
    SSE Endpoint that streams agent flow events.
    Events: text, tool_start, tool_result, error
    """
    async def event_generator():
        try:
            async for event in agent.stream_ask(question):
                # Format for SSE
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.error(f"Error during streaming: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/reset")
async def reset_agent():
    logger.info("Resetting agent conversation history.")
    agent.reset_conversation()
    return {"status": "success", "message": "Conversation history cleared."}

@app.get("/api/sessions")
async def list_sessions():
    """Returns a list of all saved sessions."""
    return {"status": "success", "sessions": agent.session_manager.list_sessions()}

@app.get("/api/session/{session_id}")
async def get_session_history(session_id: str):
    """Returns the full history for a specific session."""
    session_data = agent.session_manager.get_session(session_id)
    if not session_data:
        return {"status": "error", "message": "Session not found."}
    
    # Set the active session_id so the user can continue this conversation
    agent.session_id = session_id
    return {"status": "success", "session": session_data}

@app.post("/api/session/{session_id}/rename")
async def rename_session(session_id: str, request: RenameRequest):
    """Renames a session."""
    success = agent.session_manager.rename_session(session_id, request.title)
    if not success:
        return {"status": "error", "message": "Session not found."}
    return {"status": "success", "title": request.title}

@app.get("/skills")
async def get_skills():
    """Returns the list of currently loaded skills."""
    skills = getattr(agent, "loaded_skills", [])
    logger.debug(f"UI requested loaded skills. Returning {len(skills)} skills.")
    return {"status": "success", "skills": skills}

# Serve static files (UI)
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)