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
from agent.skills_agent import SkillsSQLAgent

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
agent = SkillsSQLAgent()


@app.get("/stream")
async def stream_agent(question: str):
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
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/reset")
async def reset_agent():
    agent.reset_conversation()
    return {"status": "success", "message": "Conversation history cleared."}

# Serve static files (UI)
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)