"""
Production-grade LLM provider with:
- Structured JSON output parsing
- Exponential backoff retry with configurable attempts
- Token usage & cost tracking
"""

import json
import re
import time
import logging
from typing import Optional

from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import SystemMessage, HumanMessage

from support_ticket_classification_system.core.config import Settings
from support_ticket_classification_system.prompts.prompt_registry import get_prompt
from support_ticket_classification_system.services.validation import validate_output

logger = logging.getLogger(__name__)


def _get_llm() -> ChatNVIDIA:
    """Initialize the ChatNVIDIA LLM instance."""
    return ChatNVIDIA(
        model=Settings.MODEL_NAME,
        nvidia_api_key=Settings.NVIDIA_API_KEY,
        temperature=0,
    )


def _parse_json_response(raw_text: str) -> dict:
    """
    Extract and parse JSON from LLM response.
    Handles common issues: markdown fences, leading/trailing text, etc.
    """
    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    cleaned = re.sub(r"```(?:json)?\s*", "", raw_text).strip()
    cleaned = re.sub(r"```\s*$", "", cleaned).strip()

    # Try to find JSON object boundaries
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1

    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in LLM response: {raw_text[:200]}")

    json_str = cleaned[start:end]
    return json.loads(json_str)


def _extract_cost(response) -> dict:
    """
    Extract token usage from the LLM response metadata and compute estimated cost.
    """
    metadata = getattr(response, "response_metadata", {}) or {}
    usage = metadata.get("token_usage", {})

    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", 0)

    # Compute estimated cost
    input_cost = (prompt_tokens / 1_000_000) * Settings.COST_PER_1M_INPUT_TOKENS
    output_cost = (completion_tokens / 1_000_000) * Settings.COST_PER_1M_OUTPUT_TOKENS
    estimated_cost = round(input_cost + output_cost, 8)

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": estimated_cost,
    }


def classify_ticket(text: str, prompt_version: Optional[str] = None) -> dict:
    """
    Classify a support ticket using the LLM with retry, validation, and cost tracking.

    Args:
        text: The (PII-masked) ticket text to classify.
        prompt_version: Which prompt version to use (defaults to Settings.DEFAULT_PROMPT_VERSION).

    Returns:
        {
            "output": { validated classification dict },
            "cost": { token usage and cost },
            "retry_count": int,
            "validated": bool,
            "prompt_version": str,
        }
    """
    version = prompt_version or Settings.DEFAULT_PROMPT_VERSION
    prompt_config = get_prompt(version)
    llm = _get_llm()

    messages = [
        SystemMessage(content=prompt_config["system"]),
        HumanMessage(content=text),
    ]

    last_error = None
    total_cost = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "estimated_cost_usd": 0.0}

    for attempt in range(1, Settings.RETRY_ATTEMPTS + 1):
        try:
            logger.info("LLM attempt %d/%d (prompt: %s)", attempt, Settings.RETRY_ATTEMPTS, version)

            response = llm.invoke(messages)
            raw_text = response.content

            # ── Accumulate cost across retries ──
            attempt_cost = _extract_cost(response)
            total_cost["prompt_tokens"] += attempt_cost["prompt_tokens"]
            total_cost["completion_tokens"] += attempt_cost["completion_tokens"]
            total_cost["total_tokens"] += attempt_cost["total_tokens"]
            total_cost["estimated_cost_usd"] = round(
                total_cost["estimated_cost_usd"] + attempt_cost["estimated_cost_usd"], 8
            )

            # ── Parse JSON ──
            parsed = _parse_json_response(raw_text)

            # ── Validate against Pydantic schema ──
            validated_dict, is_valid, error_msg = validate_output(parsed)

            if is_valid:
                return {
                    "output": validated_dict,
                    "cost": total_cost,
                    "retry_count": attempt,
                    "validated": True,
                    "prompt_version": version,
                }

            # Validation failed — retry
            last_error = f"Validation error: {error_msg}"
            logger.warning("Attempt %d failed validation: %s", attempt, error_msg)

        except json.JSONDecodeError as e:
            last_error = f"JSON parse error: {e}"
            logger.warning("Attempt %d — invalid JSON: %s", attempt, e)

        except Exception as e:
            last_error = f"LLM error: {e}"
            logger.warning("Attempt %d — LLM call failed: %s", attempt, e)

        # ── Exponential backoff before retry (skip on last attempt) ──
        if attempt < Settings.RETRY_ATTEMPTS:
            delay = Settings.RETRY_BASE_DELAY * (2 ** (attempt - 1))
            logger.info("Retrying in %.1fs...", delay)
            time.sleep(delay)

    # ── All retries exhausted — return fallback ──
    logger.error("All %d attempts failed. Last error: %s", Settings.RETRY_ATTEMPTS, last_error)

    return {
        "output": {
            "category": "General Inquiry",
            "priority": "Medium",
            "assigned_team": "General Support",
            "sentiment": "Neutral",
            "confidence_score": 0.0,
        },
        "cost": total_cost,
        "retry_count": Settings.RETRY_ATTEMPTS,
        "validated": False,
        "prompt_version": version,
        "fallback_reason": last_error,
    }