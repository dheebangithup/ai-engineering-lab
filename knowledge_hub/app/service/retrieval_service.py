"""
RetrievalService: Orchestrates query execution, context assembly, and prompt provisioning.

Pipeline:
    User Query
      │
      ▼
    1. Query Processing (SearchRequest validation)
      │
      ▼
    2. Retrieval (VectorStore similarity search)
      │
      ▼
    3. Context Builder (Dedup → Sort → Expand → Merge → Budget → Format)
      │
      ▼
    4. Prompt Provisioning (PromptRegistry versioned template binding)
      │
      ▼
    5. Response Assembly (SearchResponse + BuiltContext + RenderedPrompt)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from knowledge_hub.app.prompts.context_builder import (
    BuiltContext,
    ContextBuilder,
    ContextBuilderConfig,
    SortStrategy,
)
from knowledge_hub.app.database.vector_store import VectorStore
from knowledge_hub.app.model import SearchRequest, SearchResponse
from knowledge_hub.app.model.api_reponse import ApiResponse, ResponseBuilder
from knowledge_hub.app.prompts import RenderedPrompt, prompt_registry
from knowledge_hub.app.service.document_metadata_service import DocumentMetaDataService

logger = logging.getLogger("app")


# ---------------------------------------------------------------------------
# Response model: wraps raw results + assembled context + rendered prompt
# ---------------------------------------------------------------------------
@dataclass
class RetrievalResult:
    """
    Unified response returned by RetrievalService.

    Attributes:
        search_response: Raw ranked chunks from the vector store.
        built_context:   Fully processed context string ready for LLM consumption.
        rendered_prompt: Optional versioned prompt rendered with context & query.
    """
    search_response: SearchResponse
    built_context: BuiltContext
    rendered_prompt: RenderedPrompt | None = None


# ---------------------------------------------------------------------------
# RetrievalService
# ---------------------------------------------------------------------------
class RetrievalService:
    """
    Retrieves relevant chunks from the vector store, runs them through
    the enterprise ContextBuilder pipeline, and optionally provisions versioned prompts.

    Constructor args:
        document_metadata_service: Service for fetching document-level metadata.
        vector_store:              Qdrant-backed vector similarity search.
        context_builder_config:    Optional fallback pipeline config.
    """

    def __init__(
        self,
        document_metadata_service: DocumentMetaDataService,
        vector_store: VectorStore,
        context_builder_config: ContextBuilderConfig | None = None,
    ):
        self.__metadata_service = document_metadata_service
        self.__vector_store = vector_store
        self.__context_builder_config = context_builder_config
        logger.info(
            "RetrievalService: initialised | custom_cb_config=%s",
            context_builder_config is not None,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(
        self,
        option: SearchRequest,
    ) -> ApiResponse[RetrievalResult] | ApiResponse[None]:
        """
        Execute end-to-end retrieval, context assembly, and optional prompt provisioning.

        Args:
            option: SearchRequest containing query, vector params, context_builder overrides,
                    and optional prompt provisioning params.

        Returns:
            ApiResponse[RetrievalResult] on success.
            ApiResponse[None] on validation failure or unhandled exception.
        """
        logger.info(
            "RetrievalService.search: starting | query='%s' top_k=%d "
            "score_threshold=%.3f max_context_tokens=%d prompt_name=%s prompt_version=%s",
            option.query, option.top_k, option.score_threshold, option.max_context_tokens,
            option.prompt_name, option.prompt_version,
        )

        # ── 1. Validation ─────────────────────────────────────────────────
        validation_error = self._validate_request(option)
        if validation_error:
            logger.warning("RetrievalService.search: validation failed — %s", validation_error)
            return ResponseBuilder.failure(validation_error)

        try:
            # ── 2. Vector Store Retrieval ──────────────────────────────────
            logger.debug("RetrievalService.search: querying vector store")
            search_response: SearchResponse = self.__vector_store.search(option)

            if not search_response or not search_response.results:
                logger.info(
                    "RetrievalService.search: vector store returned 0 results for query='%s'",
                    option.query,
                )
                empty_context = BuiltContext(
                    context_str="",
                    sources=[],
                    token_count=0,
                    chunk_count=0,
                    pipeline_stats={"input_count": 0},
                )
                return ResponseBuilder.success(
                    RetrievalResult(
                        search_response=search_response,
                        built_context=empty_context,
                        rendered_prompt=None,
                    ),
                    "No matching documents found",
                )

            logger.info(
                "RetrievalService.search: vector store returned %d raw candidates",
                len(search_response.results),
            )

            # ── 3. Context Builder Pipeline ────────────────────────────────
            cb_config = self._resolve_context_builder_config(option)
            context_builder = ContextBuilder(config=cb_config)

            logger.debug("RetrievalService.search: invoking ContextBuilder pipeline")
            built_context = context_builder.build(search_response.results)

            if built_context.is_empty:
                logger.warning(
                    "RetrievalService.search: ContextBuilder produced empty context "
                    "for query='%s' (all chunks dropped by pipeline)", option.query,
                )

            # ── 4. Optional Prompt Provisioning ───────────────────────────
            rendered_prompt: RenderedPrompt | None = None
            if option.prompt_name:
                try:
                    prompt_vars = {
                        "context": built_context.context_str,
                        "query": option.query,
                    }
                    if option.additional_prompt_vars:
                        prompt_vars.update(option.additional_prompt_vars)

                    logger.debug(
                        "RetrievalService.search: provisioning prompt '%s' [version=%s]",
                        option.prompt_name, option.prompt_version or "active",
                    )
                    rendered_prompt = prompt_registry.render(
                        name=option.prompt_name,
                        variables=prompt_vars,
                        version=option.prompt_version,
                    )
                    logger.info(
                        "RetrievalService.search: provisioned prompt '%s' [v%s]",
                        rendered_prompt.prompt_name, rendered_prompt.version,
                    )
                except Exception as pe:
                    logger.error(
                        "RetrievalService.search: failed to provision prompt '%s': %s",
                        option.prompt_name, str(pe),
                        exc_info=True,
                    )
                    return ResponseBuilder.failure(f"Prompt provisioning failed: {str(pe)}")

            logger.info(
                "RetrievalService.search: pipeline done | "
                "raw_chunks=%d context_chunks=%d tokens=%d prompt_provisioned=%s stats=%s",
                len(search_response.results),
                built_context.chunk_count,
                built_context.token_count,
                rendered_prompt is not None,
                built_context.pipeline_stats,
            )

            # ── 5. Assemble response ───────────────────────────────────────
            result = RetrievalResult(
                search_response=search_response,
                built_context=built_context,
                rendered_prompt=rendered_prompt,
            )
            return ResponseBuilder.success(result, "success")

        except Exception as e:
            logger.error(
                "RetrievalService.search: unhandled exception during retrieval for query='%s': %s",
                option.query, str(e),
                exc_info=True,
            )
            return ResponseBuilder.failure("An internal error occurred during retrieval.")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_request(option: SearchRequest) -> str | None:
        """
        Returns a human-readable error message if the request is invalid,
        or None if validation passes.
        """
        if not option.query or not option.query.strip():
            return "Query string must not be empty."
        if option.top_k < 1 or option.top_k > 100:
            return f"top_k must be between 1 and 100; got {option.top_k}."
        if not (0.0 <= option.score_threshold <= 1.0):
            return f"score_threshold must be between 0.0 and 1.0; got {option.score_threshold}."
        if option.max_context_tokens < 100:
            return f"max_context_tokens must be ≥ 100; got {option.max_context_tokens}."
        return None

    def _resolve_context_builder_config(self, option: SearchRequest) -> ContextBuilderConfig:
        """
        Builds a ContextBuilderConfig by merging API request payloads with fallbacks.
        If option.context_builder payload is provided, API parameters take highest precedence.
        """
        if option.context_builder is not None:
            logger.debug(
                "RetrievalService: resolved ContextBuilderConfig directly from API request payload | sort=%s max_tokens=%d",
                option.context_builder.sort_strategy.value, option.context_builder.max_context_tokens,
            )
            return option.context_builder

        if self.__context_builder_config is not None:
            cfg = ContextBuilderConfig(
                max_context_tokens=option.max_context_tokens,
                sort_strategy=self.__context_builder_config.sort_strategy,
                enable_adjacent_expansion=self.__context_builder_config.enable_adjacent_expansion,
                adjacency_window=self.__context_builder_config.adjacency_window,
                enable_chunk_merging=self.__context_builder_config.enable_chunk_merging,
                max_merge_gap=self.__context_builder_config.max_merge_gap,
                include_source_header=self.__context_builder_config.include_source_header,
                include_chunk_separator=self.__context_builder_config.include_chunk_separator,
                chunk_separator=self.__context_builder_config.chunk_separator,
                source_header_template=self.__context_builder_config.source_header_template,
                min_score_threshold=option.score_threshold,
            )
            logger.debug(
                "RetrievalService: resolved ContextBuilderConfig from global config with per-request token_budget=%d",
                option.max_context_tokens,
            )
            return cfg

        cfg = ContextBuilderConfig(
            max_context_tokens=option.max_context_tokens,
            sort_strategy=SortStrategy.SCORE_DESC,
            enable_chunk_merging=True,
            min_score_threshold=option.score_threshold,
        )
        logger.debug(
            "RetrievalService: resolved default ContextBuilderConfig | max_tokens=%d score_threshold=%.3f",
            option.max_context_tokens, option.score_threshold,
        )
        return cfg
