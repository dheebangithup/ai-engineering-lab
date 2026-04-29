import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ── LLM Provider ──
    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
    MODEL_NAME = os.getenv("MODEL_NAME", "meta/llama-3.1-8b-instruct")

    # ── Retry / Resilience ──
    RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", 3))
    RETRY_BASE_DELAY = float(os.getenv("RETRY_BASE_DELAY", 1.0))  # seconds

    # ── PII ──
    PII_DETECTION_ENABLED = os.getenv("PII_DETECTION_ENABLED", "true").lower() == "true"

    # ── Prompt Versioning ──
    DEFAULT_PROMPT_VERSION = os.getenv("DEFAULT_PROMPT_VERSION", "v2")

    # ── Cost Tracking (per 1M tokens, approximate for NVIDIA NIM) ──
    COST_PER_1M_INPUT_TOKENS = float(os.getenv("COST_PER_1M_INPUT_TOKENS", 0.10))
    COST_PER_1M_OUTPUT_TOKENS = float(os.getenv("COST_PER_1M_OUTPUT_TOKENS", 0.30))


Settings = Settings()