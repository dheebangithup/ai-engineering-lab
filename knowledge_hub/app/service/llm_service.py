"""
LlmService: Enterprise LLM service powered by LangChain ChatOpenAI.
Connects to local LM Studio or external OpenAI-compatible endpoints.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from knowledge_hub.app.config import app_settings
from knowledge_hub.app.prompts.rendered_prompt import RenderedPrompt

logger = logging.getLogger("app")


@dataclass
class LLMGenerationResult:
    """
    Standardized container for LLM generation response.

    Attributes:
        answer: Generated text response from the model.
        model_name: Identifier of the model used.
        latency_ms: Execution time in milliseconds.
        usage: Optional token usage/metadata dictionary from response.
    """
    answer: str
    model_name: str
    latency_ms: float
    usage: Optional[dict[str, Any]] = None


class LlmService:
    """
    Enterprise LLM Service wrapper for LangChain ChatOpenAI and ChatGroq.

    Constructor accepts overrides or defaults to configuration in app_settings.
    """

    def __init__(
        self,
        provider: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
    ):
        self._provider = provider or app_settings.LLM_PROVIDER
        self._base_url = base_url
        self._api_key = api_key
        self._model = model or app_settings.LLM_MODEL
        self._temperature = (
            temperature if temperature is not None else app_settings.LOCAL_LM_TEMPERATURE
        )

        logger.info(
            "LlmService: initializing | provider='%s' model='%s' temperature=%.2f",
            self._provider,
            self._model,
            self._temperature,
        )

        self._chat_model, self._resolved_model_name = self._create_model(
            provider=self._provider,
            model=self._model,
            temperature=self._temperature,
            api_key=self._api_key,
            base_url=self._base_url
        )

    def _create_model(
        self,
        provider: str,
        model: str,
        temperature: float,
        api_key: str | None = None,
        base_url: str | None = None
    ) -> tuple[Any, str]:
        """
        Instantiates the underlying LangChain chat client and resolves the target model name.
        """
        prov = provider.lower()
        if prov == "groq":
            from langchain_groq import ChatGroq
            key = api_key or app_settings.GROQ_API_KEY
            if not key:
                logger.error("LlmService initialization failed: GROQ_API_KEY is not configured")
                raise ValueError("Groq API key is missing in configuration.")
            
            # Default model for Groq if not specified or standard default model
            m = model
            if m == "qwen2.5-7b-instruct-1m:3" or not m:
                # If model is the default LM Studio qwen, override with llama-3.1-8b-instant for Groq
                m = "llama-3.1-8b-instant"
                
            logger.info("Initializing ChatGroq client model='%s' temp=%.2f", m, temperature)
            return ChatGroq(
                api_key=key,
                model=m,
                temperature=temperature
            ), m
        elif prov == "openai":
            logger.info("Initializing ChatOpenAI client model='%s' temp=%.2f", model, temperature)
            return ChatOpenAI(
                model=model or "gpt-4-turbo",
                temperature=temperature
            ), model or "gpt-4-turbo"
        else:
            # default to lm_studio / OpenAI local endpoint
            url = base_url or app_settings.LOCAL_LM_URL
            key = api_key or app_settings.LOCAL_LM_API_KEY or "lm-studio"
            m = model or app_settings.LOCAL_LM_CHAT_MODEL
            logger.info("Initializing ChatOpenAI client pointing to Local LM Studio: url='%s' model='%s' temp=%.2f", url, m, temperature)
            return ChatOpenAI(
                base_url=url,
                api_key=key,
                model=m,
                temperature=temperature
            ), m

    def generate_answer(
        self,
        rendered_prompt: RenderedPrompt,
        temperature_override: float | None = None,
    ) -> LLMGenerationResult:
        """
        Invokes the LangChain ChatOpenAI or ChatGroq model using system and user prompts.

        Args:
            rendered_prompt: Standardized RenderedPrompt instance containing system_prompt & user_prompt.
            temperature_override: Optional per-request temperature override.

        Returns:
            LLMGenerationResult on success.

        Raises:
            RuntimeError on LLM invocation failure.
        """
        start_time = time.perf_counter()
        eff_temperature = (
            temperature_override if temperature_override is not None else self._temperature
        )

        logger.info(
            "LlmService.generate_answer: starting | provider='%s' model='%s' prompt_name='%s' version='%s' temp=%.2f",
            self._provider,
            self._resolved_model_name,
            rendered_prompt.prompt_name,
            rendered_prompt.version,
            eff_temperature,
        )

        messages: list[BaseMessage] = []
        if rendered_prompt.system_prompt:
            messages.append(SystemMessage(content=rendered_prompt.system_prompt))
        messages.append(HumanMessage(content=rendered_prompt.user_prompt))

        try:
            active_model = self._chat_model
            resolved_name = self._resolved_model_name
            if temperature_override is not None and temperature_override != self._temperature:
                logger.debug(
                    "LlmService.generate_answer: applying temperature override=%.2f",
                    temperature_override,
                )
                active_model, resolved_name = self._create_model(
                    provider=self._provider,
                    model=self._model,
                    temperature=temperature_override,
                    api_key=self._api_key,
                    base_url=self._base_url
                )

            logger.debug(
                "LlmService.generate_answer: invoking LangChain client with %d messages",
                len(messages),
            )

            ai_message = active_model.invoke(messages)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            answer_content = str(ai_message.content)
            response_meta = getattr(ai_message, "response_metadata", {})

            logger.info(
                "LlmService.generate_answer: success | answer_chars=%d latency_ms=%.2f",
                len(answer_content),
                latency_ms,
            )

            return LLMGenerationResult(
                answer=answer_content,
                model_name=resolved_name,
                latency_ms=latency_ms,
                usage=response_meta if isinstance(response_meta, dict) else None,
            )

        except Exception as e:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                "LlmService.generate_answer: failed | model='%s' latency_ms=%.2f error: %s",
                self._resolved_model_name,
                latency_ms,
                str(e),
                exc_info=True,
            )
            raise RuntimeError(f"LLM generation failed: {str(e)}") from e
