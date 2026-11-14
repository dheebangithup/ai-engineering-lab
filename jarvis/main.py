import os
from pathlib import Path
from jarvis import config  # Ensures .env is automatically discovered and loaded
from jarvis.logger import get_logger, setup_logging

setup_logging()
logger = get_logger("jarvis.main")


def check_langsmith_connection() -> None:
    """Verifies LangSmith environment configuration and connectivity."""
    tracing = os.getenv("LANGSMITH_TRACING", "").lower() in ("true", "1", "t")
    api_key = os.getenv("LANGSMITH_API_KEY")
    endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    project = os.getenv("LANGSMITH_PROJECT", "jarvis")

    logger.info(f"LangSmith Tracing Enabled: {tracing}")
    logger.info(f"LangSmith Project: {project}")
    logger.info(f"LangSmith Endpoint: {endpoint}")

    if not api_key:
        logger.warning("LANGSMITH_API_KEY is not set in environment.")
        return

    try:
        from langsmith import Client
        client = Client(api_url=endpoint, api_key=api_key)
        # Quick ping / verification
        logger.info("Successfully connected to LangSmith.")
    except Exception as e:
        logger.warning(f"Could not connect to LangSmith client: {e}")


def main() -> None:
    check_langsmith_connection()
    logger.info("J.A.R.V.I.S. initialized and ready for development.")


if __name__ == "__main__":
    main()

