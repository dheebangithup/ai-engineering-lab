"""
Support Ticket Classification System - Main Entry Point (Web UI)
"""

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os
import sys

from support_ticket_classification_system.graph.graph import app as ticket_app

# Get absolute path to the static directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

server = FastAPI(title="AI Ticket Classifier UI")

# Basic Request Model
class TicketRequest(BaseModel):
    text: str
    prompt_version: str = "v2"

@server.post("/classify")
async def classify(request: TicketRequest):
    # Invoke the LangGraph pipeline
    result = ticket_app.invoke({
        "text": request.text,
        "prompt_version": request.prompt_version
    })
    return result

@server.get("/")
async def get_ui():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        return {"error": f"UI file not found at {index_path}. Please ensure 'static/index.html' exists."}
    return FileResponse(index_path)

# Serve static files if needed
if os.path.exists(STATIC_DIR):
    server.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def main():
    """Start the Web UI server."""
    print("\n" + "=" * 65)
    print("  🚀 STARTING SUPPORT TICKET CLASSIFICATION WEB UI")
    print("  Access at: http://localhost:8000")
    print("=" * 65 + "\n")
    uvicorn.run(server, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
