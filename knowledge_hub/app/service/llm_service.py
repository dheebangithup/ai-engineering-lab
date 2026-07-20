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
    Enterprise LLM Service wrapper for LangChain ChatOpenAI.

    Constructor accepts overrides or defaults to configuration in app_settings.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
    ):
        self._base_url = base_url or app_settings.LOCAL_LM_URL
        self._api_key = api_key or app_settings.LOCAL_LM_API_KEY
        self._model = model or app_settings.LOCAL_LM_CHAT_MODEL
        self._temperature = (
            temperature if temperature is not None else app_settings.LOCAL_LM_TEMPERATURE
        )

        logger.info(
            "LlmService: initialized | base_url='%s' model='%s' temperature=%.2f",
            self._base_url,
            self._model,
            self._temperature,
        )

        self._chat_model = ChatOpenAI(
            base_url=self._base_url,
            api_key=self._api_key,
            model=self._model,
            temperature=self._temperature,
        )

    def generate_answer(
        self,
        rendered_prompt: RenderedPrompt,
        temperature_override: float | None = None,
    ) -> LLMGenerationResult:
        """
        Invokes the LangChain ChatOpenAI model using system and user prompts from RenderedPrompt.

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
            "LlmService.generate_answer: starting | model='%s' prompt_name='%s' version='%s' temp=%.2f",
            self._model,
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
            if temperature_override is not None and temperature_override != self._temperature:
                logger.debug(
                    "LlmService.generate_answer: applying temperature override=%.2f",
                    temperature_override,
                )
                active_model = ChatOpenAI(
                    base_url=self._base_url,
                    api_key=self._api_key,
                    model=self._model,
                    temperature=temperature_override,
                )

            logger.debug(
                "LlmService.generate_answer: invoking LangChain ChatOpenAI with %d messages",
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
                model_name=self._model,
                latency_ms=latency_ms,
                usage=response_meta if isinstance(response_meta, dict) else None,
            )

        except Exception as e:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                "LlmService.generate_answer: failed | model='%s' latency_ms=%.2f error: %s",
                self._model,
                latency_ms,
                str(e),
                exc_info=True,
            )
            raise RuntimeError(f"LLM generation failed: {str(e)}") from e
