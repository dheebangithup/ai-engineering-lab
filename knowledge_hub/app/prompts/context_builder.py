"""
Enterprise-grade Context Builder Pipeline for RAG systems.

Pipeline Flow:
    Raw SearchResults
          │
          ▼
    1. Deduplicator          → Remove exact duplicate chunks by chunk_id / content hash
          │
          ▼
    2. ChunkSorter           → Sort by relevance score (DESC) or document order (page_number ASC)
          │
          ▼
    3. AdjacentChunkExpander → Expand context by fetching ±N neighboring chunks (future: DB lookup)
          │
          ▼
    4. ChunkMerger           → Merge consecutive chunks from the same document/page into one block
          │
          ▼
    5. TokenBudgetManager    → Enforce token budget, drop lowest-scored chunks when over limit
          │
          ▼
    6. PromptFormatter       → Assemble final context string with citations and structure
          │
          ▼
    BuiltContext (context_str, sources, token_count, pipeline_stats)
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from pydantic import BaseModel, Field

from knowledge_hub.app.config import app_settings
from knowledge_hub.app.model.search_response import SearchResult

logger = logging.getLogger("app")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_AVG_CHARS_PER_TOKEN = 4  # Conservative estimate; use tiktoken when available
_DEFAULT_ADJACENCY_WINDOW = 1   # ±1 chunk neighbours
_MAX_MERGE_GAP = 1               # merge consecutive chunks whose index diff ≤ this


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class SortStrategy(str, Enum):
    """Sort strategy applied to retrieved chunks before further processing."""
    SCORE_DESC = "score_desc"          # Highest relevance first (default for RAG)
    DOCUMENT_ORDER = "document_order"  # Natural reading order: (source, page, chunk_index)
    HYBRID = "hybrid"                  # Score-first within same document, then doc order


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------
@dataclass
class SourceCitation:
    """Represents a single source reference in the built context."""
    file_name: str
    source: str
    page_number: int
    chunk_index: int
    score: float


@dataclass
class BuiltContext:
    """Final output of the ContextBuilder pipeline."""
    context_str: str                                   # Formatted context ready for LLM prompt
    sources: list[SourceCitation] = field(default_factory=list)
    token_count: int = 0                               # Estimated tokens used
    chunk_count: int = 0                               # Number of chunks after all processing
    pipeline_stats: dict = field(default_factory=dict) # Per-stage counters for observability

    @property
    def is_empty(self) -> bool:
        return not self.context_str.strip()


class ContextBuilderConfig(BaseModel):
    """
    Central configuration object for the ContextBuilder pipeline.
    Serves as both domain config and Pydantic model for API request payloads.
    """
    max_context_tokens: int = Field(
        default_factory=lambda: app_settings.MAX_CONTEXT_TOKENS,
        description="Maximum token budget allowed for built context.",
        ge=100
    )
    sort_strategy: SortStrategy = Field(
        SortStrategy.SCORE_DESC,
        description="Sort strategy for context chunks ('score_desc', 'document_order', 'hybrid')."
    )
    enable_adjacent_expansion: bool = Field(
        False,
        description="Whether to expand retrieved chunks by fetching ±N adjacent neighbours."
    )
    adjacency_window: int = Field(
        1,
        description="Adjacency window size (±N neighbours).",
        ge=1
    )
    enable_chunk_merging: bool = Field(
        True,
        description="Whether to merge consecutive chunks from the same document/page."
    )
    max_merge_gap: int = Field(
        1,
        description="Maximum gap between chunk indices to merge consecutive chunks.",
        ge=1
    )
    include_source_header: bool = Field(
        True,
        description="Whether to prepend source metadata header to each chunk block."
    )
    include_chunk_separator: bool = Field(
        True,
        description="Whether to insert separators between formatted chunk blocks."
    )
    chunk_separator: str = Field(
        "\n\n---\n\n",
        description="Separator string placed between formatted chunk blocks."
    )
    source_header_template: str = Field(
        "[Source: {file_name} | Page {page_number} | Chunk #{chunk_index}]",
        description="Template string for context chunk headers."
    )
    min_score_threshold: float = Field(
        default_factory=lambda: app_settings.DEFAULT_SCORE_THRESHOLD,
        description="Minimum vector similarity score threshold.",
        ge=0.0,
        le=1.0
    )


# ---------------------------------------------------------------------------
# Stage 1: Deduplicator
# ---------------------------------------------------------------------------
class Deduplicator:
    """
    Removes duplicate chunks from the retrieved results.

    Dedup strategy (in order of precedence):
      1. By chunk_id (UUID) — exact match
      2. By content fingerprint (MD5 of stripped text) — catches rephrased duplicates
         that map to the same raw chunk
    """

    def run(self, results: list[SearchResult]) -> list[SearchResult]:
        logger.debug("Deduplicator: starting with %d candidates", len(results))
        seen_chunk_ids: set[str] = set()
        seen_fingerprints: set[str] = set()
        unique: list[SearchResult] = []

        for result in results:
            chunk = result.document
            chunk_id_str = str(chunk.chunk_id)
            fingerprint = self._content_fingerprint(chunk.content)

            if chunk_id_str in seen_chunk_ids:
                logger.debug(
                    "Deduplicator: dropping duplicate chunk_id=%s (file=%s page=%d)",
                    chunk_id_str, chunk.file_name, chunk.page_number,
                )
                continue

            if fingerprint in seen_fingerprints:
                logger.debug(
                    "Deduplicator: dropping content-duplicate chunk_id=%s (file=%s page=%d)",
                    chunk_id_str, chunk.file_name, chunk.page_number,
                )
                continue

            seen_chunk_ids.add(chunk_id_str)
            seen_fingerprints.add(fingerprint)
            unique.append(result)

        removed = len(results) - len(unique)
        logger.info(
            "Deduplicator: %d → %d results (removed %d duplicates)",
            len(results), len(unique), removed,
        )
        return unique

    @staticmethod
    def _content_fingerprint(text: str) -> str:
        normalized = " ".join(text.split()).lower()
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Stage 2: ChunkSorter
# ---------------------------------------------------------------------------
class ChunkSorter:
    """
    Sorts retrieved chunks according to the configured strategy.

    - SCORE_DESC:     Pure relevance ranking — best for most RAG use cases.
    - DOCUMENT_ORDER: Natural reading order — better for summarisation / long-doc QA.
    - HYBRID:         Groups by (source, doc_version), sorts groups by best score,
                      then within each group preserves reading order.
    """

    def __init__(self, strategy: SortStrategy = SortStrategy.SCORE_DESC):
        self._strategy = strategy
        logger.debug("ChunkSorter: initialised with strategy=%s", strategy.value)

    def run(self, results: list[SearchResult]) -> list[SearchResult]:
        logger.debug("ChunkSorter: sorting %d chunks using strategy=%s", len(results), self._strategy.value)

        if self._strategy == SortStrategy.SCORE_DESC:
            sorted_results = sorted(results, key=lambda r: r.score, reverse=True)

        elif self._strategy == SortStrategy.DOCUMENT_ORDER:
            sorted_results = sorted(
                results,
                key=lambda r: (r.document.source, r.document.page_number, r.document.chuk_index),
            )

        elif self._strategy == SortStrategy.HYBRID:
            # Group by document, rank groups by their best score, then sort within group by page/index
            groups: dict[str, list[SearchResult]] = {}
            for r in results:
                key = f"{r.document.source}::{r.document.doc_version}"
                groups.setdefault(key, []).append(r)

            ranked_groups = sorted(
                groups.values(),
                key=lambda grp: max(r.score for r in grp),
                reverse=True,
            )
            sorted_results = []
            for grp in ranked_groups:
                grp.sort(key=lambda r: (r.document.page_number, r.document.chuk_index))
                sorted_results.extend(grp)
        else:
            logger.warning("ChunkSorter: unknown strategy '%s', falling back to SCORE_DESC", self._strategy)
            sorted_results = sorted(results, key=lambda r: r.score, reverse=True)

        logger.info("ChunkSorter: sorted %d chunks [strategy=%s]", len(sorted_results), self._strategy.value)
        return sorted_results


# ---------------------------------------------------------------------------
# Stage 3: AdjacentChunkExpander
# ---------------------------------------------------------------------------
class AdjacentChunkExpander:
    """
    Expands each retrieved chunk by fetching its ±window neighbours for richer context.

    Production note:
        The full implementation requires a chunk store lookup (e.g. Qdrant scroll by
        document_id + adjacent chunk_index). A `chunk_fetcher` callable is accepted as
        a dependency-injected hook so the caller can wire in the real store without
        coupling this class to any specific DB.

        Signature: chunk_fetcher(document_id: str, chunk_index: int) -> Optional[SearchResult]
    """

    def __init__(
        self,
        window: int = _DEFAULT_ADJACENCY_WINDOW,
        chunk_fetcher: Optional[Callable[[str, int], Optional[SearchResult]]] = None,
    ):
        self._window = window
        self._chunk_fetcher = chunk_fetcher
        if chunk_fetcher is None:
            logger.info(
                "AdjacentChunkExpander: no chunk_fetcher provided — "
                "expansion will be skipped (pass chunk_fetcher to enable)"
            )

    def run(self, results: list[SearchResult]) -> list[SearchResult]:
        if self._chunk_fetcher is None:
            logger.debug("AdjacentChunkExpander: skipping — no chunk_fetcher wired")
            return results

        logger.debug(
            "AdjacentChunkExpander: expanding %d chunks with window=±%d",
            len(results), self._window,
        )

        existing_chunk_ids = {str(r.document.chunk_id) for r in results}
        expanded: list[SearchResult] = list(results)
        added = 0

        for result in results:
            doc = result.document
            for offset in range(-self._window, self._window + 1):
                if offset == 0:
                    continue
                neighbour_index = doc.chuk_index + offset
                if neighbour_index < 0:
                    continue
                try:
                    neighbour = self._chunk_fetcher(doc.document_id, neighbour_index)
                    if neighbour and str(neighbour.document.chunk_id) not in existing_chunk_ids:
                        existing_chunk_ids.add(str(neighbour.document.chunk_id))
                        expanded.append(neighbour)
                        added += 1
                        logger.debug(
                            "AdjacentChunkExpander: added neighbour chunk_index=%d for doc_id=%s",
                            neighbour_index, doc.document_id,
                        )
                except Exception:
                    logger.warning(
                        "AdjacentChunkExpander: failed to fetch neighbour doc_id=%s chunk_index=%d",
                        doc.document_id, neighbour_index,
                        exc_info=True,
                    )

        logger.info(
            "AdjacentChunkExpander: %d → %d results (added %d neighbours)",
            len(results), len(expanded), added,
        )
        return expanded


# ---------------------------------------------------------------------------
# Stage 4: ChunkMerger
# ---------------------------------------------------------------------------
class ChunkMerger:
    """
    Merges consecutive chunks from the same document into a single logical block.

    Merge criteria (ALL must hold):
      - Same document_id AND same source
      - Chunk indices are contiguous (gap ≤ max_merge_gap)
      - Same page_number (configurable — set max_merge_gap higher to span pages)

    Result: fewer, larger chunks with a synthetic score = max(merged scores).
    This reduces prompt fragmentation and citation noise.
    """

    def __init__(self, max_merge_gap: int = _MAX_MERGE_GAP):
        self._max_merge_gap = max_merge_gap

    def run(self, results: list[SearchResult]) -> list[SearchResult]:
        if not results:
            logger.debug("ChunkMerger: no results to merge")
            return results

        logger.debug("ChunkMerger: attempting to merge %d chunks (max_gap=%d)", len(results), self._max_merge_gap)

        # Sort into document reading order before merging
        ordered = sorted(
            results,
            key=lambda r: (r.document.source, r.document.page_number, r.document.chuk_index),
        )

        merged: list[SearchResult] = []
        current = ordered[0]

        for nxt in ordered[1:]:
            c_doc = current.document
            n_doc = nxt.document

            same_document = (c_doc.document_id == n_doc.document_id and c_doc.source == n_doc.source)
            same_page = c_doc.page_number == n_doc.page_number
            consecutive = abs(n_doc.chuk_index - c_doc.chuk_index) <= self._max_merge_gap

            if same_document and same_page and consecutive:
                logger.debug(
                    "ChunkMerger: merging chunk_index=%d into chunk_index=%d (doc=%s page=%d)",
                    n_doc.chuk_index, c_doc.chuk_index, c_doc.document_id, c_doc.page_number,
                )
                # Build a merged SearchResult — mutate a copy of current's document
                merged_content = c_doc.content.rstrip() + " " + n_doc.content.lstrip()
                merged_score = max(current.score, nxt.score)

                from dataclasses import replace as dc_replace
                from knowledge_hub.app.model.search_response import SearchResult as SR
                from knowledge_hub.app.model.chunk_payload import ChunkPayload

                merged_payload = ChunkPayload(
                    document_id=c_doc.document_id,
                    chunk_id=c_doc.chunk_id,           # keep the first chunk's id as anchor
                    page_number=c_doc.page_number,
                    source=c_doc.source,
                    file_name=c_doc.file_name,
                    content=merged_content,
                    doc_version=c_doc.doc_version,
                    chuk_index=c_doc.chuk_index,
                )
                current = SR(document=merged_payload, score=merged_score)
            else:
                merged.append(current)
                current = nxt

        merged.append(current)

        removed = len(results) - len(merged)
        logger.info(
            "ChunkMerger: %d → %d chunks (merged %d consecutive chunks)",
            len(results), len(merged), removed,
        )
        return merged


# ---------------------------------------------------------------------------
# Stage 5: TokenBudgetManager
# ---------------------------------------------------------------------------
class TokenBudgetManager:
    """
    Enforces a maximum token budget for the assembled context.

    Strategy:
      1. Estimate tokens per chunk using `_estimate_tokens`.
      2. Greedily include chunks in current order until budget is exhausted.
      3. Log every chunk that is dropped, with its score and token count.

    Production upgrade path:
      Replace `_estimate_tokens` with `tiktoken.encoding_for_model(model_name).encode()`
      for byte-pair-encoding–accurate counts.
    """

    def __init__(self, max_tokens: int | None = None):
        self._max_tokens = max_tokens if max_tokens is not None else app_settings.MAX_CONTEXT_TOKENS
        logger.debug("TokenBudgetManager: initialised with max_tokens=%d", self._max_tokens)

    def run(self, results: list[SearchResult]) -> tuple[list[SearchResult], int]:
        """Returns (trimmed_results, total_estimated_tokens)."""
        logger.debug("TokenBudgetManager: applying budget of %d tokens to %d chunks", self._max_tokens, len(results))

        kept: list[SearchResult] = []
        running_tokens = 0

        for result in results:
            chunk_tokens = self._estimate_tokens(result.document.content)
            if running_tokens + chunk_tokens <= self._max_tokens:
                kept.append(result)
                running_tokens += chunk_tokens
                logger.debug(
                    "TokenBudgetManager: accepted chunk_id=%s tokens=%d running=%d",
                    result.document.chunk_id, chunk_tokens, running_tokens,
                )
            else:
                logger.info(
                    "TokenBudgetManager: budget exceeded — dropping chunk_id=%s "
                    "(chunk_tokens=%d, running=%d, budget=%d, score=%.4f)",
                    result.document.chunk_id, chunk_tokens, running_tokens,
                    self._max_tokens, result.score,
                )

        logger.info(
            "TokenBudgetManager: %d → %d chunks | estimated_tokens=%d / %d",
            len(results), len(kept), running_tokens, self._max_tokens,
        )
        return kept, running_tokens

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """
        Fast heuristic: ~4 chars per token (GPT-3/4 average).
        Replace with tiktoken for production accuracy.
        """
        return max(1, len(text) // _AVG_CHARS_PER_TOKEN)


# ---------------------------------------------------------------------------
# Stage 6: PromptFormatter
# ---------------------------------------------------------------------------
class PromptFormatter:
    """
    Assembles the final context string from processed chunks, with:
      - A per-chunk source header for citation traceability
      - Configurable chunk separators
      - A numbered source list appended at the end
      - Structured BuiltContext output (not just a raw string)
    """

    def __init__(self, config: ContextBuilderConfig):
        self._config = config

    def run(
        self,
        results: list[SearchResult],
        token_count: int,
        pipeline_stats: dict,
    ) -> BuiltContext:
        if not results:
            logger.warning("PromptFormatter: received empty results list — returning empty context")
            return BuiltContext(
                context_str="",
                sources=[],
                token_count=0,
                chunk_count=0,
                pipeline_stats=pipeline_stats,
            )

        logger.debug("PromptFormatter: formatting %d chunks into context", len(results))

        blocks: list[str] = []
        sources: list[SourceCitation] = []

        for idx, result in enumerate(results, start=1):
            doc = result.document
            header = ""
            if self._config.include_source_header:
                header = self._config.source_header_template.format(
                    file_name=doc.file_name,
                    page_number=doc.page_number,
                    chunk_index=doc.chuk_index,
                ) + "\n"

            blocks.append(f"{header}{doc.content.strip()}")

            sources.append(SourceCitation(
                file_name=doc.file_name,
                source=doc.source,
                page_number=doc.page_number,
                chunk_index=doc.chuk_index,
                score=round(result.score, 4),
            ))

        separator = self._config.chunk_separator if self._config.include_chunk_separator else "\n\n"
        context_str = separator.join(blocks)

        logger.info(
            "PromptFormatter: assembled context | chunks=%d token_estimate=%d",
            len(results), token_count,
        )

        return BuiltContext(
            context_str=context_str,
            sources=sources,
            token_count=token_count,
            chunk_count=len(results),
            pipeline_stats=pipeline_stats,
        )


# ---------------------------------------------------------------------------
# Orchestrator: ContextBuilder
# ---------------------------------------------------------------------------
class ContextBuilder:
    """
    Orchestrates the full context-building pipeline.

    Usage:
        config = ContextBuilderConfig(
            max_context_tokens=4096,
            sort_strategy=SortStrategy.HYBRID,
            enable_chunk_merging=True,
        )
        builder = ContextBuilder(config)
        built_context = builder.build(search_results)

    With adjacent expansion (requires DB-backed fetcher):
        builder = ContextBuilder(config, chunk_fetcher=my_vector_store.fetch_by_index)
        built_context = builder.build(search_results)
    """

    def __init__(
        self,
        config: Optional[ContextBuilderConfig] = None,
        chunk_fetcher: Optional[Callable[[str, int], Optional[SearchResult]]] = None,
    ):
        self._config = config or ContextBuilderConfig()
        self._deduplicator = Deduplicator()
        self._sorter = ChunkSorter(strategy=self._config.sort_strategy)
        self._expander = AdjacentChunkExpander(
            window=self._config.adjacency_window,
            chunk_fetcher=chunk_fetcher if self._config.enable_adjacent_expansion else None,
        )
        self._merger = ChunkMerger(max_merge_gap=self._config.max_merge_gap)
        self._budget_manager = TokenBudgetManager(max_tokens=self._config.max_context_tokens)
        self._formatter = PromptFormatter(config=self._config)

        logger.info(
            "ContextBuilder: initialised | max_tokens=%d sort=%s merge=%s expansion=%s",
            self._config.max_context_tokens,
            self._config.sort_strategy.value,
            self._config.enable_chunk_merging,
            self._config.enable_adjacent_expansion,
        )

    def build(self, raw_results: list[SearchResult]) -> BuiltContext:
        """
        Execute the full pipeline and return a BuiltContext.

        Args:
            raw_results: Direct output from vector store similarity search.

        Returns:
            BuiltContext with formatted context string, citations, token count and stats.
        """
        pipeline_start = time.perf_counter()
        stats: dict = {"input_count": len(raw_results)}

        logger.info("ContextBuilder.build: starting pipeline with %d raw results", len(raw_results))

        if not raw_results:
            logger.warning("ContextBuilder.build: received empty raw_results — returning empty context")
            return BuiltContext(context_str="", pipeline_stats=stats)

        # ── Pre-filter by score threshold ──────────────────────────────────
        if self._config.min_score_threshold > 0.0:
            before = len(raw_results)
            raw_results = [r for r in raw_results if r.score >= self._config.min_score_threshold]
            dropped = before - len(raw_results)
            if dropped:
                logger.info(
                    "ContextBuilder.build: pre-filter dropped %d chunks below score_threshold=%.3f",
                    dropped, self._config.min_score_threshold,
                )
            stats["below_threshold_dropped"] = dropped

        # ── Stage 1: Deduplicate ───────────────────────────────────────────
        stage_start = time.perf_counter()
        results = self._deduplicator.run(raw_results)
        stats["after_dedup"] = len(results)
        stats["dedup_ms"] = round((time.perf_counter() - stage_start) * 1000, 2)

        # ── Stage 2: Sort ──────────────────────────────────────────────────
        stage_start = time.perf_counter()
        results = self._sorter.run(results)
        stats["after_sort"] = len(results)
        stats["sort_ms"] = round((time.perf_counter() - stage_start) * 1000, 2)

        # ── Stage 3: Adjacent Expansion ────────────────────────────────────
        stage_start = time.perf_counter()
        results = self._expander.run(results)
        stats["after_expansion"] = len(results)
        stats["expansion_ms"] = round((time.perf_counter() - stage_start) * 1000, 2)

        # ── Stage 4: Merge ─────────────────────────────────────────────────
        stage_start = time.perf_counter()
        if self._config.enable_chunk_merging:
            results = self._merger.run(results)
        else:
            logger.debug("ContextBuilder.build: chunk merging disabled — skipping")
        stats["after_merge"] = len(results)
        stats["merge_ms"] = round((time.perf_counter() - stage_start) * 1000, 2)

        # ── Stage 5: Token Budget ──────────────────────────────────────────
        stage_start = time.perf_counter()
        results, token_count = self._budget_manager.run(results)
        stats["after_budget"] = len(results)
        stats["token_count"] = token_count
        stats["budget_ms"] = round((time.perf_counter() - stage_start) * 1000, 2)

        # ── Stage 6: Format ────────────────────────────────────────────────
        stage_start = time.perf_counter()
        total_ms = round((time.perf_counter() - pipeline_start) * 1000, 2)
        stats["format_ms"] = round((time.perf_counter() - stage_start) * 1000, 2)
        stats["total_pipeline_ms"] = total_ms

        built = self._formatter.run(results, token_count, stats)

        logger.info(
            "ContextBuilder.build: pipeline complete | "
            "input=%d → output_chunks=%d tokens=%d total_ms=%.2f",
            stats["input_count"], built.chunk_count, built.token_count, total_ms,
        )

        if built.is_empty:
            logger.warning(
                "ContextBuilder.build: pipeline produced an empty context "
                "(all chunks dropped by dedup/budget/threshold)"
            )

        return built
