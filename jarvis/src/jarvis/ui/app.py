"""
Main entry point for starting the J.A.R.V.I.S. Web UI server.
"""

import os
import sys
from pathlib import Path
import uvicorn

src_dir = Path(__file__).resolve().parent.parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

os.environ["PYTHONPATH"] = f"{str(src_dir)}:{os.environ.get('PYTHONPATH', '')}"


from jarvis.logger import get_logger, setup_logging

setup_logging()
logger = get_logger("ui.app")


def run(host: Optional[str] = None, port: Optional[int] = None, reload: bool = True):
    """Start the Uvicorn web server."""
    h = host or os.getenv("HOST", "0.0.0.0")
    p = port or int(os.getenv("PORT", "8000"))
    logger.info(f"Launching Uvicorn server on http://{h}:{p} (reload={reload})")
    try:
        uvicorn.run(
            "jarvis.ui.server:app",
            host=h,
            port=p,
            reload=reload,
            app_dir=str(src_dir),
        )
    except OSError as e:
        if e.errno == 48:
            logger.error(f"Port {p} is already in use by another process. Use PORT={p+1} to run on another port.")
            print(f"\n[ERROR] Port {p} is in use. Try: PORT={p+1} uv run python app.py\n")
        else:
            logger.error(f"Server error: {e}", exc_info=True)
            print(f"\n[ERROR] Server error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    from typing import Optional
    run()
