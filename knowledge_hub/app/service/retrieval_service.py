"""
RetrievalService: Orchestrates query execution, context assembly, prompt provisioning, and LLM text generation.

Retrieval Modes:
    DENSE  → Vector similarity search only (Qdrant cosine)
    BM25   → BM25 keyword search only (sparse retrieval via langchain_community)
    HYBRID → Dense + BM25 fused via Reciprocal Rank Fusion (RRF)

Pipeline:
    User Query
      │
      ▼
    1. Query Processing (SearchRequest validation)
      │
      ▼
    2. Retrieval Mode Router (Dense / BM25 / Hybrid+RRF)
      │
      ▼
    3. Context Builder (Dedup → Sort → Expand → Merge → Budget → Format)
      │
      ▼
    4. Prompt Provisioning (PromptRegistry versioned template binding)
      │
      ▼
    5. LLM Generation (LangChain ChatOpenAI call via LlmService)
      │
      ▼
    6. Response Assembly (SearchResponse + BuiltContext + RenderedPrompt + LLMGenerationResult)
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Optional

from knowledge_hub.app.prompts.context_builder import (
    BuiltContext,
    ContextBuilder,
    ContextBuilderConfig,
    SortStrategy,
)
from knowledge_hub.app.database.vector_store import VectorStore
from knowledge_hub.app.enums.retrieval_mode import RetrievalMode
from knowledge_hub.app.model import SearchRequest, SearchResponse
from knowledge_hub.app.model.api_reponse import ApiResponse, ResponseBuilder
from knowledge_hub.app.model.search_response import SearchResult
from knowledge_hub.app.model.chunk_payload import ChunkPayload
from knowledge_hub.app.prompts import RenderedPrompt, prompt_registry
from knowledge_hub.app.service.document_metadata_service import DocumentMetaDataService
from knowledge_hub.app.service.llm_service import LlmService, LLMGenerationResult

logger = logging.getLogger("app")


# ---------------------------------------------------------------------------
# Response model: wraps raw results + assembled context + rendered prompt + LLM answer
# ---------------------------------------------------------------------------
@dataclass
class RetrievalResult:
    """
    Unified response returned by RetrievalService.

    Attributes:
        search_response: Raw ranked chunks from the vector store.
        built_context:   Fully processed context string ready for LLM consumption.
        rendered_prompt: Optional versioned prompt rendered with context & query.
        llm_response:    Optional LLM generated answer from LangChain ChatOpenAI.
    """
    search_response: SearchResponse
    built_context: BuiltContext
    rendered_prompt: RenderedPrompt | None = None
    llm_response: LLMGenerationResult | None = None


# ---------------------------------------------------------------------------
# RetrievalService
# ---------------------------------------------------------------------------
class RetrievalService:
    """
    Retrieves relevant chunks from the vector store, runs them through
    the enterprise ContextBuilder pipeline, provisions versioned prompts,
    and optionally generates answers using LangChain ChatOpenAI.
    """

    def __init__(
        self,
        document_metadata_service: DocumentMetaDataService,
        vector_store: VectorStore,
        context_builder_config: ContextBuilderConfig | None = None,
        llm_service: LlmService | None = None,
        bm25_service=None,
    ):
        self.__metadata_service = document_metadata_service
        self.__vector_store = vector_store
        self.__context_builder_config = context_builder_config
        self.__llm_service = llm_service or LlmService()
        self.__bm25_service = bm25_service
        logger.info(
            "RetrievalService: initialised | custom_cb_config=%s custom_llm_service=%s bm25_enabled=%s",
            context_builder_config is not None,
            llm_service is not None,
            bm25_service is not None,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(
        self,
        option: SearchRequest,
    ) -> ApiResponse[RetrievalResult] | ApiResponse[None]:
        """
        Execute end-to-end retrieval, context assembly, prompt provisioning, and optional LLM text generation.

        Args:
            option: SearchRequest containing query, vector params, context_builder overrides,
                    prompt provisioning params, and enable_llm_generation flag.

        Returns:
            ApiResponse[RetrievalResult] on success.
            ApiResponse[None] on validation failure or unhandled exception.
        """
        eff_enable_llm = (
            option.enable_llm_generation
            if option.enable_llm_generation is not None
            else (option.prompt_name is not None)
        )

        # Resolve retrieval mode
        try:
            retrieval_mode = RetrievalMode(option.retrieval_mode)
        except ValueError:
            logger.warning(
                "RetrievalService.search: invalid retrieval_mode '%s', falling back to DENSE",
                option.retrieval_mode,
            )
            retrieval_mode = RetrievalMode.DENSE

        logger.info(
            "RetrievalService.search: starting | query='%s' top_k=%d "
            "score_threshold=%.3f max_context_tokens=%d retrieval_mode=%s "
            "bm25_weight=%.2f dense_weight=%.2f prompt_name=%s prompt_version=%s enable_llm=%s",
            option.query, option.top_k, option.score_threshold, option.max_context_tokens,
            retrieval_mode.value, option.bm25_weight, option.dense_weight,
            option.prompt_name, option.prompt_version, eff_enable_llm,
        )

        # ── 1. Validation ─────────────────────────────────────────────────
        validation_error = self._validate_request(option, retrieval_mode)
        if validation_error:
            logger.warning("RetrievalService.search: validation failed — %s", validation_error)
            return ResponseBuilder.failure(validation_error)

        try:
            # ── 2. Retrieval Mode Router ───────────────────────────────────
            search_response = self._execute_retrieval(option, retrieval_mode)

            if not search_response or not search_response.results:
                logger.info(
                    "RetrievalService.search: retrieval returned 0 results for query='%s' mode=%s",
                    option.query, retrieval_mode.value,
                )
                empty_context = BuiltContext(
                    context_str="",
                    sources=[],
                    token_count=0,
                    chunk_count=0,
                    pipeline_stats={"input_count": 0, "retrieval_mode": retrieval_mode.value},
                )
                return ResponseBuilder.success(
                    RetrievalResult(
                        search_response=search_response,
                        built_context=empty_context,
                        rendered_prompt=None,
                        llm_response=None,
                    ),
                    "No matching documents found",
                )

            logger.info(
                "RetrievalService.search: retrieval returned %d raw candidates (mode=%s)",
                len(search_response.results), retrieval_mode.value,
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

            # Inject retrieval mode and extra metadata stats
            built_context.pipeline_stats["retrieval_mode"] = retrieval_mode.value
            if search_response.metadata:
                built_context.pipeline_stats.update(search_response.metadata)

            # ── 4. Optional Prompt Provisioning ───────────────────────────
            rendered_prompt: RenderedPrompt | None = None
            eff_enable_llm = (
                option.enable_llm_generation
                if option.enable_llm_generation is not None
                else (option.prompt_name is not None)
            )
            eff_prompt_name = option.prompt_name or ("rag_qa" if eff_enable_llm else None)

            if eff_prompt_name:
                try:
                    prompt_vars = {
                        "context": built_context.context_str,
                        "query": option.query,
                    }
                    if option.additional_prompt_vars:
                        prompt_vars.update(option.additional_prompt_vars)

                    logger.debug(
                        "RetrievalService.search: provisioning prompt '%s' [version=%s]",
                        eff_prompt_name, option.prompt_version or "active",
                    )
                    rendered_prompt = prompt_registry.render(
                        name=eff_prompt_name,
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
                        eff_prompt_name, str(pe),
                        exc_info=True,
                    )
                    return ResponseBuilder.failure(f"Prompt provisioning failed: {str(pe)}")

            # ── 5. Optional LLM Generation ─────────────────────────────────
            llm_result: LLMGenerationResult | None = None
            if eff_enable_llm:
                if not rendered_prompt:
                    logger.error("RetrievalService.search: LLM generation requested but no rendered prompt available")
                    return ResponseBuilder.failure("LLM generation requested but prompt rendering failed")

                try:
                    logger.info("RetrievalService.search: invoking LLM via LlmService")
                    llm_result = self.__llm_service.generate_answer(
                        rendered_prompt=rendered_prompt,
                        temperature_override=option.temperature,
                    )
                    logger.info(
                        "RetrievalService.search: LLM generation completed | model=%s latency_ms=%.2f",
                        llm_result.model_name, llm_result.latency_ms,
                    )
                except Exception as le:
                    logger.error(
                        "RetrievalService.search: LLM generation error: %s",
                        str(le), exc_info=True,
                    )
                    return ResponseBuilder.failure(f"LLM generation error: {str(le)}")

            logger.info(
                "RetrievalService.search: pipeline done | "
                "raw_chunks=%d context_chunks=%d tokens=%d prompt_provisioned=%s llm_generated=%s stats=%s",
                len(search_response.results),
                built_context.chunk_count,
                built_context.token_count,
                rendered_prompt is not None,
                llm_result is not None,
                built_context.pipeline_stats,
            )

            # ── 6. Assemble response ───────────────────────────────────────
            result = RetrievalResult(
                search_response=search_response,
                built_context=built_context,
                rendered_prompt=rendered_prompt,
                llm_response=llm_result,
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
    def _validate_request(option: SearchRequest, retrieval_mode: RetrievalMode = RetrievalMode.DENSE) -> str | None:
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
        if option.temperature is not None and not (0.0 <= option.temperature <= 2.0):
            return f"temperature must be between 0.0 and 2.0; got {option.temperature}."
        if retrieval_mode == RetrievalMode.HYBRID:
            if not (0.0 <= option.bm25_weight <= 1.0):
                return f"bm25_weight must be between 0.0 and 1.0; got {option.bm25_weight}."
            if not (0.0 <= option.dense_weight <= 1.0):
                return f"dense_weight must be between 0.0 and 1.0; got {option.dense_weight}."
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

    # ------------------------------------------------------------------
    # Retrieval Mode Router
    # ------------------------------------------------------------------
    def _execute_retrieval(
        self, option: SearchRequest, retrieval_mode: RetrievalMode
    ) -> SearchResponse:
        """
        Routes the search request to the appropriate retrieval backend
        based on the configured retrieval mode.
        """
        if retrieval_mode == RetrievalMode.DENSE:
            logger.debug("RetrievalService: executing DENSE vector retrieval")
            return self.__vector_store.search(option)

        elif retrieval_mode == RetrievalMode.BM25:
            if self.__bm25_service is None:
                logger.error(
                    "RetrievalService: BM25 retrieval mode requested but no BM25 service is configured. "
                    "Falling back to DENSE mode."
                )
                return self.__vector_store.search(option)

            if not self.__bm25_service.is_index_ready:
                logger.warning(
                    "RetrievalService: BM25 index is not ready. Falling back to DENSE mode."
                )
                return self.__vector_store.search(option)

            logger.debug("RetrievalService: executing BM25 keyword retrieval")
            return self.__bm25_service.search(option.query, top_k=option.top_k)

        elif retrieval_mode == RetrievalMode.HYBRID:
            return self._hybrid_search(option)

        else:
            logger.warning(
                "RetrievalService: unknown retrieval_mode '%s', falling back to DENSE",
                retrieval_mode,
            )
            return self.__vector_store.search(option)

    # ------------------------------------------------------------------
    # Hybrid Search with Reciprocal Rank Fusion
    # ------------------------------------------------------------------
    def _hybrid_search(self, option: SearchRequest) -> SearchResponse:
        """
        Performs hybrid retrieval by combining dense vector search and BM25
        keyword search results using Reciprocal Rank Fusion (RRF).

        RRF Score = Σ weight_i * (1 / (k + rank_i))
        where k=60 is the RRF constant to prevent top-ranked items from
        dominating the fused score.
        """
        from knowledge_hub.app.config import app_settings

        if self.__bm25_service is None or not self.__bm25_service.is_index_ready:
            logger.warning(
                "RetrievalService._hybrid_search: BM25 service unavailable or index not ready. "
                "Falling back to dense-only retrieval."
            )
            return self.__vector_store.search(option)

        # Fetch more candidates from each retriever for better fusion
        bm25_top_k = max(option.top_k, int(option.top_k * app_settings.BM25_TOP_K_MULTIPLIER))
        dense_top_k = option.top_k

        logger.info(
            "RetrievalService._hybrid_search: executing hybrid search | "
            "dense_top_k=%d bm25_top_k=%d dense_weight=%.2f bm25_weight=%.2f",
            dense_top_k, bm25_top_k, option.dense_weight, option.bm25_weight,
        )

        # 1. Dense vector search
        try:
            dense_response = self.__vector_store.search(option)
            dense_results = dense_response.results if dense_response and dense_response.results else []
            logger.info(
                "RetrievalService._hybrid_search: dense search returned %d candidates",
                len(dense_results),
            )
        except Exception as e:
            logger.error(
                "RetrievalService._hybrid_search: dense search failed: %s",
                str(e), exc_info=True,
            )
            dense_results = []

        # 2. BM25 keyword search
        try:
            bm25_response = self.__bm25_service.search(option.query, top_k=bm25_top_k)
            bm25_results = bm25_response.results if bm25_response and bm25_response.results else []
            logger.info(
                "RetrievalService._hybrid_search: BM25 search returned %d candidates",
                len(bm25_results),
            )
        except Exception as e:
            logger.error(
                "RetrievalService._hybrid_search: BM25 search failed: %s",
                str(e), exc_info=True,
            )
            bm25_results = []

        # 3. If one retriever returned nothing, use the other's results directly
        if not dense_results and not bm25_results:
            logger.info("RetrievalService._hybrid_search: both retrievers returned 0 results")
            return SearchResponse(results=[], metadata={"dense_count": 0, "bm25_count": 0, "fused_count": 0})
        if not dense_results:
            logger.info("RetrievalService._hybrid_search: dense returned 0, using BM25 results only")
            return SearchResponse(
                results=bm25_results[:option.top_k],
                metadata={"dense_count": 0, "bm25_count": len(bm25_results), "fused_count": len(bm25_results[:option.top_k])}
            )
        if not bm25_results:
            logger.info("RetrievalService._hybrid_search: BM25 returned 0, using dense results only")
            return SearchResponse(
                results=dense_results[:option.top_k],
                metadata={"dense_count": len(dense_results), "bm25_count": 0, "fused_count": len(dense_results[:option.top_k])}
            )

        # 4. Reciprocal Rank Fusion
        fused_results = self._reciprocal_rank_fusion(
            dense_results=dense_results,
            bm25_results=bm25_results,
            dense_weight=option.dense_weight,
            bm25_weight=option.bm25_weight,
            top_k=option.top_k,
        )

        logger.info(
            "RetrievalService._hybrid_search: RRF fusion complete | "
            "dense_count=%d bm25_count=%d fused_count=%d",
            len(dense_results), len(bm25_results), len(fused_results),
        )
        return SearchResponse(
            results=fused_results,
            metadata={
                "dense_count": len(dense_results),
                "bm25_count": len(bm25_results),
                "fused_count": len(fused_results)
            }
        )

    @staticmethod
    def _reciprocal_rank_fusion(
        dense_results: list[SearchResult],
        bm25_results: list[SearchResult],
        dense_weight: float = 0.7,
        bm25_weight: float = 0.3,
        top_k: int = 5,
        rrf_k: int = 60,
    ) -> list[SearchResult]:
        """
        Reciprocal Rank Fusion (RRF) algorithm.

        For each result in each retriever:
            rrf_score += weight * (1 / (rrf_k + rank))

        where rrf_k is a constant (default 60) that prevents top-ranked items
        from dominating the fused ranking.

        Args:
            dense_results: Results from dense vector search (ordered by score desc).
            bm25_results: Results from BM25 keyword search (ordered by relevance).
            dense_weight: Weight for dense retriever in fusion.
            bm25_weight: Weight for BM25 retriever in fusion.
            top_k: Number of fused results to return.
            rrf_k: RRF constant (default 60 per the original RRF paper).

        Returns:
            List of SearchResult sorted by fused RRF score descending.
        """
        # chunk_id -> (fused_score, best_SearchResult)
        fused_scores: dict[str, tuple[float, SearchResult]] = {}

        # Process dense results
        for rank, result in enumerate(dense_results):
            chunk_key = str(result.document.chunk_id)
            rrf_score = dense_weight * (1.0 / (rrf_k + rank + 1))

            if chunk_key in fused_scores:
                existing_score, existing_result = fused_scores[chunk_key]
                fused_scores[chunk_key] = (existing_score + rrf_score, existing_result)
            else:
                fused_scores[chunk_key] = (rrf_score, result)

        # Process BM25 results
        for rank, result in enumerate(bm25_results):
            chunk_key = str(result.document.chunk_id)
            rrf_score = bm25_weight * (1.0 / (rrf_k + rank + 1))

            if chunk_key in fused_scores:
                existing_score, existing_result = fused_scores[chunk_key]
                fused_scores[chunk_key] = (existing_score + rrf_score, existing_result)
            else:
                fused_scores[chunk_key] = (rrf_score, result)

        # Sort by fused score descending and build final results
        sorted_items = sorted(fused_scores.values(), key=lambda x: x[0], reverse=True)

        final_results: list[SearchResult] = []
        for fused_score, original_result in sorted_items[:top_k]:
            # Create a new SearchResult with the fused score
            final_results.append(
                SearchResult(
                    document=original_result.document,
                    score=round(fused_score, 6),
                )
            )

        logger.info(
            "RetrievalService._reciprocal_rank_fusion: merged %d unique chunks → top %d | "
            "dense_weight=%.2f bm25_weight=%.2f rrf_k=%d",
            len(fused_scores), len(final_results),
            dense_weight, bm25_weight, rrf_k,
        )
        return final_results
