import os

from langchain_groq import ChatGroq


DEFAULT_MODEL = "openai/gpt-oss-120b"


def create_groq_llm(
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
) -> ChatGroq:
    """
    Create the Groq chat model used by the J.A.R.V.I.S. agent.

    GROQ_API_KEY must be available in the environment.
    """

    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError(
            "GROQ_API_KEY environment variable is not set"
        )

    return ChatGroq(
        model=model,
        temperature=temperature,
    )