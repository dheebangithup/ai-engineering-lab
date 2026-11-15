"""
J.A.R.V.I.S. Web Application Launcher.
Starts the FastAPI server with Uvicorn and hosts the modern Iron Man HUD dashboard at http://localhost:8000.
"""

import os
import sys
import uvicorn
from jarvis.logger import setup_logging

setup_logging()


def start_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = True) -> None:
    print("\n" + "=" * 65)
    print(" 🚀 Launching J.A.R.V.I.S. Personal AI Agent Web Application")
    print(f" 🌐 Dashboard & Command Console: http://localhost:{port}")
    print(f" 📚 OpenAPI Documentation:       http://localhost:{port}/docs")
    print("=" * 65 + "\n")
    uvicorn.run("jarvis.interfaces.api:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    reload_env = os.getenv("RELOAD", "true").lower() in ("true", "1")
    start_server(port=port, reload=reload_env)
