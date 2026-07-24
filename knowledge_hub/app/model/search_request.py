"""
SearchRequest Pydantic Model for API retrieval endpoints.
Exposes ContextBuilderConfig, Prompt Provisioning, and LLM Generation controls directly via API.
"""

from typing import Optional, Any
from pydantic import BaseModel, Field
from knowledge_hub.app.config import app_settings
from knowledge_hub.app.prompts.context_builder import ContextBuilderConfig
from knowledge_hub.app.enums.retrieval_mode import RetrievalMode


class SearchRequest(BaseModel):
    query: str = Field(
        ...,
        description="Natural language query string.",
        examples=["What is Multi-Head Attention?"]
    )
    top_k: int = Field(
        default_factory=lambda: app_settings.DEFAULT_TOP_K,
        description="Number of nearest vector candidates to retrieve.",
        ge=1,
        le=100
    )
    score_threshold: float = Field(
        default_factory=lambda: app_settings.DEFAULT_SCORE_THRESHOLD,
        description="Minimum similarity score threshold (0.0 to 1.0).",
        ge=0.0,
        le=1.0
    )
    max_context_tokens: int = Field(
        default_factory=lambda: app_settings.MAX_CONTEXT_TOKENS,
        description="Maximum context tokens allowed.",
        ge=100
    )
    filters: Optional[dict[str, Any]] = Field(
        None,
        description="Optional metadata key-value filters for document filtering."
    )

    # Retrieval Pipeline Mode
    retrieval_mode: str = Field(
        default_factory=lambda: app_settings.DEFAULT_RETRIEVAL_MODE,
        description="Retrieval pipeline mode: 'dense' (vector only), 'bm25' (keyword only), or 'hybrid' (dense + BM25 RRF fusion)."
    )
    bm25_weight: float = Field(
        default_factory=lambda: app_settings.DEFAULT_BM25_WEIGHT,
        description="Weight for BM25 results in hybrid RRF fusion (0.0 to 1.0).",
        ge=0.0,
        le=1.0
    )
    dense_weight: float = Field(
        default_factory=lambda: app_settings.DEFAULT_DENSE_WEIGHT,
        description="Weight for dense vector results in hybrid RRF fusion (0.0 to 1.0).",
        ge=0.0,
        le=1.0
    )

    # Directly reuse ContextBuilderConfig for API configuration overrides
    context_builder: Optional[ContextBuilderConfig] = Field(
        None,
        description="ContextBuilder configuration overrides."
    )

    # Prompt Provisioning controls
    prompt_name: Optional[str] = Field(
        None,
        description="Name of prompt template to provision (e.g. 'rag_qa')."
    )
    prompt_version: Optional[str] = Field(
        None,
        description="Version of prompt template (e.g. 'v1.1.0' or 'v1.0.0'). If omitted, active version is used."
    )
    additional_prompt_vars: Optional[dict[str, Any]] = Field(
        None,
        description="Additional custom variables passed during prompt template rendering."
    )

    # LLM Generation controls
    enable_llm_generation: Optional[bool] = Field(
        None,
        description="Whether to execute LLM text generation using rendered prompt and local LM Studio. Defaults to True when prompt_name is set."
    )
    temperature: Optional[float] = Field(
        None,
        description="Optional sampling temperature override for LLM generation (e.g., 0.7).",
        ge=0.0,
        le=2.0
    )
