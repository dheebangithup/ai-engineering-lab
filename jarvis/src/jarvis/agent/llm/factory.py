import os
from typing import Any, Optional

from langchain_core.language_models.chat_models import BaseChatModel

from jarvis.agent.llm.groq import create_groq_llm
from jarvis.agent.llm.kodekloud import create_kodekloud_llm
from jarvis.logger import get_logger

logger = get_logger("llm.factory")

DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "kodekloud").lower().strip()
DEFAULT_MODEL = os.getenv("LLM_MODEL", "gpt-oss-120b")


def get_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.0,
    **kwargs: Any,
) -> BaseChatModel:
    """
    Central factory to obtain configured LLM instances across the JARVIS project.
    Supported providers: 'kodekloud', 'groq'.
    Defaults to KodeKloud's gpt-oss-120b model.
    """
    selected_provider = (provider or DEFAULT_PROVIDER).lower().strip()

    if selected_provider == "kodekloud":
        model_name = model or DEFAULT_MODEL
        logger.info(f"Instantiating KodeKloud LLM: model='{model_name}', temp={temperature}")
        return create_kodekloud_llm(model=model_name, temperature=temperature, **kwargs)
    elif selected_provider == "groq":
        model_name = model or "openai/gpt-oss-120b"
        logger.info(f"Instantiating Groq LLM: model='{model_name}', temp={temperature}")
        return create_groq_llm(model=model_name, temperature=temperature, **kwargs)
    elif selected_provider == "qwen":
        model_name = model or "qwen/qwen3.8-flash"
        logger.info(f"Instantiating Qwen LLM via KodeKloud: model='{model_name}', temp={temperature}")
        return create_kodekloud_llm(model=model_name, temperature=temperature, **kwargs)
    else:
        logger.error(f"Unsupported LLM provider requested: '{selected_provider}'")
        raise ValueError(
            f"Unsupported LLM provider: '{selected_provider}'. Supported: ['kodekloud', 'groq', 'qwen']"
        )


def get_default_llm() -> BaseChatModel:
    """
    Get the default LLM for JARVIS agents.
    Returns gpt-oss-120b from KodeKloud by default.
    """
    return get_llm(provider=DEFAULT_PROVIDER, model=DEFAULT_MODEL)
