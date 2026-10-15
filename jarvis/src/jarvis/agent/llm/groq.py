import os
from typing import Optional

from jarvis.config import load_env
from langchain_groq import ChatGroq

# Auto-discover and load .env regardless of working directory
load_env()


DEFAULT_MODEL = "openai/gpt-oss-120b"


def create_groq_llm(
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
    api_key: Optional[str] = None,
) -> ChatGroq:
    """
    Create the Groq chat model used by the J.A.R.V.I.S. agent.

    GROQ_API_KEY must be available in the environment / .env.
    """
    key = api_key or os.getenv("GROQ_API_KEY")
    if not key:
        load_env()
        key = api_key or os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY environment variable is not set. Please set it in your .env file."
        )

    return ChatGroq(
        model=model,
        temperature=temperature,
        api_key=key,
    )