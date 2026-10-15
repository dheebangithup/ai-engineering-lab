from jarvis.agent.llm.factory import get_default_llm, get_llm
from jarvis.agent.llm.groq import create_groq_llm
from jarvis.agent.llm.kodekloud import create_kodekloud_llm


def _resolve_kodekloud_llm():
    """Resolve KodeKloud LLM (gpt-oss-120b)."""
    return get_llm(provider="kodekloud")


def _resolve_groq_llm():
    """Resolve Groq LLM (openai/gpt-oss-120b)."""
    return get_llm(provider="groq")


def __getattr__(name: str):
    if name in ("chat_llm", "kodekloud_llm"):
        return _resolve_kodekloud_llm()
    if name in ("groq_llm", "chat_groq"):
        return _resolve_groq_llm()
    if name == "qwen_llm":
        return get_llm(provider="qwen")
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "create_kodekloud_llm",
    "create_groq_llm",
    "get_llm",
    "get_default_llm",
    "kodekloud_llm",
    "groq_llm",
    "chat_llm",
]
