import os
from pathlib import Path
from typing import Optional
import dotenv


def load_env(start_path: Optional[Path | str] = None) -> Optional[Path]:
    """
    Find and load the .env file for the J.A.R.V.I.S. project.
    
    Search order:
    1. Explicit file path from JARVIS_ENV_FILE environment variable.
    2. Upwards from start_path (or this file's directory if not specified).
    3. Upwards from the current working directory.
    """
    # 1. Explicit path in environment variable
    custom_path = os.getenv("JARVIS_ENV_FILE")
    if custom_path and Path(custom_path).is_file():
        dotenv.load_dotenv(custom_path, override=False)
        return Path(custom_path).resolve()

    # 2. Search upwards from start_path or this file's location
    origin = Path(start_path).resolve() if start_path else Path(__file__).resolve()
    for parent in [origin] + list(origin.parents):
        candidate = parent / ".env"
        if candidate.is_file():
            dotenv.load_dotenv(candidate, override=False)
            return candidate.resolve()

    # 3. Fallback to CWD search
    found = dotenv.find_dotenv(usecwd=True)
    if found:
        dotenv.load_dotenv(found, override=False)
        return Path(found).resolve()

    return None


# Auto-load on import
_loaded_env_path = load_env()
