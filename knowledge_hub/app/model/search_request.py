"""
SearchRequest Pydantic Model for API retrieval endpoints.
Exposes ContextBuilderConfig, Prompt Provisioning, and LLM Generation controls directly via API.
"""

from typing import Optional, Any
from pydantic import BaseModel, Field
from knowledge_hub.app.config import app_settings
from knowledge_hub.app.prompts.context_builder import ContextBuilderConfig


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
