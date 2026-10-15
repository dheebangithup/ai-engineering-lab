"""
Convenience entry point for running the J.A.R.V.I.S. Web App (FastAPI + HTML/CSS/JS).

Usage:
    uv run python app.py
"""

import os
import sys
import uvicorn
from pathlib import Path
# Ensure 'src' is in sys.path and PYTHONPATH
current_dir = Path(__file__).resolve().parent
src_dir = current_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

os.environ["PYTHONPATH"] = f"{str(src_dir)}:{os.environ.get('PYTHONPATH', '')}"

from jarvis.logger import get_logger, setup_logging

DEFAULT_SERVER_HOST: str = "0.0.0.0"
DEFAULT_SERVER_PORT: int = 8000
ENV_SERVER_HOST: str = "HOST"
ENV_SERVER_PORT: str = "PORT"
APP_MODULE_STRING: str = "jarvis.ui.server:app"
ERRNO_ADDRESS_ALREADY_IN_USE: int = 48

# Initialize workspace logging
setup_logging()
logger = get_logger("app")

if __name__ == "__main__":
    host = os.getenv(ENV_SERVER_HOST, DEFAULT_SERVER_HOST)
    port = int(os.getenv(ENV_SERVER_PORT, str(DEFAULT_SERVER_PORT)))
    logger.info(f"Starting J.A.R.V.I.S. application server on http://{host}:{port}...")
    try:
        uvicorn.run(
            APP_MODULE_STRING,
            host=host,
            port=port,
            reload=True,
            app_dir=str(src_dir),
        )
    except OSError as e:
        if e.errno == ERRNO_ADDRESS_ALREADY_IN_USE:
            logger.error(
                f"Port {port} is already in use by another process. "
                f"You can specify a different port via PORT environment variable (e.g., PORT=8001 uv run python app.py) "
                f"or terminate the existing process using: lsof -ti:{port} | xargs kill -9"
            )
            print(f"\n[ERROR] Port {port} is already in use. Specify another port with: PORT={port+1} uv run python app.py\n")
        else:
            logger.error(f"Failed to start server: {e}", exc_info=True)
            print(f"\n[ERROR] Failed to start server: {e}\n")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Application server encountered an unhandled exception: {e}", exc_info=True)
        print(f"\n[ERROR] Server error: {e}\n")
        sys.exit(1)
