#!/usr/bin/env python3
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
VENV_PYTHON = BASE_DIR.parent / "strata-memory" / ".venv" / "bin" / "python"

# If current python is missing uvicorn or fastapi, auto re-exec using strata-memory's .venv python
try:
    import fastapi
    import uvicorn
except ImportError:
    if VENV_PYTHON.exists() and sys.executable != str(VENV_PYTHON):
        print(f"[*] Switching to virtualenv python: {VENV_PYTHON}")
        script_file = str(Path(__file__).resolve())
        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), script_file] + sys.argv[1:])
    else:
        print("[!] Error: fastapi and uvicorn are required. Please run inside your virtualenv.")
        sys.exit(1)

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

if __name__ == "__main__":
    print("=" * 65)
    print(" 🌳 மாந்தோப்பு வாட்ச்மேன் (The Mango Grove Watchman)")
    print(" 🎮 2D Stealth AI Sandbox powered by Strata Memory & Ollama")
    print(" 👉 Open in Browser: http://localhost:8001")
    print("=" * 65)
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8001, reload=False)
