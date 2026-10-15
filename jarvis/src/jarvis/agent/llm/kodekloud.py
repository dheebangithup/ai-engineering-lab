import os
from typing import Optional

from jarvis.config import load_env
from langchain_openai import ChatOpenAI

# Auto-discover and load .env regardless of working directory
load_env()

DEFAULT_KODEKLOUD_MODEL = "gpt-oss-120b"
DEFAULT_KODEKLOUD_BASE_URL = "https://api.ai.kodekloud.com/v1"


def create_kodekloud_llm(
    model: str = DEFAULT_KODEKLOUD_MODEL,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.0,
) -> ChatOpenAI:
    """
    Create an LLM client connected to the KodeKloud AI provider.
    Reads credentials from KODEKLOUD_API_KEY in .env.
    """
    key = api_key or os.getenv("KODEKLOUD_API_KEY")
    if not key:
        load_env()
        key = api_key or os.getenv("KODEKLOUD_API_KEY")
    url = base_url or os.getenv("KODEKLOUD_BASE_URL", DEFAULT_KODEKLOUD_BASE_URL)

    if not key:
        raise RuntimeError(
            "KODEKLOUD_API_KEY not found. Please set KODEKLOUD_API_KEY in your .env file."
        )

    return ChatOpenAI(
        model=model,
        api_key=key,
        base_url=url,
        temperature=temperature,
    )
