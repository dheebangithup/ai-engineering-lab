"""
BM25RetrieverService: Manages an in-memory BM25 keyword index for sparse retrieval.

Lifecycle:
    App Startup / Ingestion Complete
        │
        ▼
    build_index()  → Fetches all chunk payloads from Qdrant via scroll_all_payloads()
        │
        ▼
    BM25Retriever  → In-memory BM25 index (rank_bm25 via langchain_community)
        │
        ▼
    search(query)  → Returns list[SearchResult] with normalized BM25 scores
"""

from __future__ import annotations

import hashlib
import logging
import time
import threading
from dataclasses import dataclass
from typing import Optional

from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document as LCDocument

from knowledge_hub.app.config import app_logger
from knowledge_hub.app.model.chunk_payload import ChunkPayload
from knowledge_hub.app.model.search_response import SearchResult, SearchResponse

logger = logging.getLogger("app")


@dataclass
class BM25IndexStats:
    """Statistics about the current BM25 index state."""
    document_count: int = 0
    build_time_ms: float = 0.0
    last_build_timestamp: float = 0.0
    is_ready: bool = False


class BM25RetrieverService:
    """
    Manages an in-memory BM25 (Best Matching 25) keyword search index
    built from chunk content stored in the Qdrant vector store.

    Thread-safe: All index mutations are protected by a threading.Lock.
    """

    def __init__(self):
        self._retriever: Optional[BM25Retriever] = None
        self._chunk_map: dict[str, ChunkPayload] = {}  # content_hash -> ChunkPayload
        self._lock = threading.Lock()
        self._stats = BM25IndexStats()
        logger.info("BM25RetrieverService: Initialized (index not yet built)")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def is_index_ready(self) -> bool:
        """Check if the BM25 index has been built and is ready for queries."""
        return self._stats.is_ready and self._retriever is not None

    @property
    def index_stats(self) -> BM25IndexStats:
        """Return current BM25 index statistics."""
        return self._stats

    # ------------------------------------------------------------------
    # Index Lifecycle
    # ------------------------------------------------------------------
    def build_index_from_payloads(self, payloads: list[dict]) -> BM25IndexStats:
        """
        Build the BM25 index from a list of Qdrant payload dicts.

        Each payload is expected to have at minimum: 'content', 'chunk_id',
        'document_id', 'page_number', 'source', 'file_name', 'doc_version', 'chuk_index'.

        Args:
            payloads: List of payload dicts from QdrantStore.scroll_all_payloads().

        Returns:
            BM25IndexStats with build metrics.
        """
        start_time = time.perf_counter()
        logger.info(
            "BM25RetrieverService: Building BM25 index from %d payloads",
            len(payloads),
        )

        if not payloads:
            logger.warning(
                "BM25RetrieverService: No payloads provided for index building. "
                "BM25 search will return empty results."
            )
            with self._lock:
                self._retriever = None
                self._chunk_map = {}
                self._stats = BM25IndexStats(
                    document_count=0,
                    build_time_ms=0.0,
                    last_build_timestamp=time.time(),
                    is_ready=False,
                )
            return self._stats

        lc_documents: list[LCDocument] = []
        chunk_map: dict[str, ChunkPayload] = {}
        skipped = 0

        for idx, payload in enumerate(payloads):
            content = payload.get("content", "")
            if not content or not content.strip():
                skipped += 1
                logger.debug(
                    "BM25RetrieverService: Skipping payload at index %d — empty content",
                    idx,
                )
                continue

            # Build ChunkPayload from the Qdrant payload dict
            try:
                chunk_payload = ChunkPayload.from_dict(payload)
            except Exception as e:
                skipped += 1
                logger.warning(
                    "BM25RetrieverService: Failed to parse payload at index %d into ChunkPayload: %s",
                    idx, str(e),
                )
                continue

            # Use content fingerprint as key for dedup and lookup
            content_hash = self._content_fingerprint(content)

            # Create LangChain Document with metadata for traceability
            lc_doc = LCDocument(
                page_content=content,
                metadata={
                    "content_hash": content_hash,
                    "chunk_id": str(chunk_payload.chunk_id),
                    "document_id": chunk_payload.document_id,
                    "page_number": chunk_payload.page_number,
                    "file_name": chunk_payload.file_name,
                },
            )
            lc_documents.append(lc_doc)
            chunk_map[content_hash] = chunk_payload

        if not lc_documents:
            logger.warning(
                "BM25RetrieverService: All %d payloads were skipped (empty content). "
                "BM25 index will not be built.",
                len(payloads),
            )
            with self._lock:
                self._retriever = None
                self._chunk_map = {}
                self._stats = BM25IndexStats(
                    document_count=0,
                    build_time_ms=round((time.perf_counter() - start_time) * 1000, 2),
                    last_build_timestamp=time.time(),
                    is_ready=False,
                )
            return self._stats

        # Build BM25 retriever from LangChain documents
        try:
            retriever = BM25Retriever.from_documents(
                lc_documents,
                k=50,  # High default k; actual top_k is applied in search()
            )
            logger.info(
                "BM25RetrieverService: BM25Retriever instance created with %d documents",
                len(lc_documents),
            )
        except Exception as e:
            logger.error(
                "BM25RetrieverService: Failed to create BM25Retriever from %d documents: %s",
                len(lc_documents), str(e),
                exc_info=True,
            )
            raise e

        # Thread-safe swap
        build_time = round((time.perf_counter() - start_time) * 1000, 2)
        with self._lock:
            self._retriever = retriever
            self._chunk_map = chunk_map
            self._stats = BM25IndexStats(
                document_count=len(lc_documents),
                build_time_ms=build_time,
                last_build_timestamp=time.time(),
                is_ready=True,
            )

        logger.info(
            "BM25RetrieverService: Index built successfully | "
            "doc_count=%d skipped=%d build_time_ms=%.2f",
            len(lc_documents), skipped, build_time,
        )
        return self._stats

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def search(self, query: str, top_k: int = 5) -> SearchResponse:
        """
        Execute BM25 keyword search and return results as SearchResponse.

        Args:
            query: Natural language query string.
            top_k: Maximum number of results to return.

        Returns:
            SearchResponse with BM25-scored SearchResult entries.
        """
        if not self.is_index_ready:
            logger.warning(
                "BM25RetrieverService: search() called but BM25 index is not ready. "
                "Returning empty results."
            )
            return SearchResponse(results=[])

        if not query or not query.strip():
            logger.warning(
                "BM25RetrieverService: search() called with empty query. Returning empty results."
            )
            return SearchResponse(results=[])

        logger.info(
            "BM25RetrieverService: Executing BM25 search | query='%s' top_k=%d",
            query, top_k,
        )

        try:
            with self._lock:
                # Set the retriever's k to top_k for this query
                self._retriever.k = top_k
                bm25_results: list[LCDocument] = self._retriever.invoke(query)

            if not bm25_results:
                logger.info(
                    "BM25RetrieverService: BM25 search returned 0 results for query='%s'",
                    query,
                )
                return SearchResponse(results=[])

            # Convert LangChain Documents back to SearchResult objects
            search_results: list[SearchResult] = []
            total_results = len(bm25_results)

            for rank, lc_doc in enumerate(bm25_results):
                content_hash = lc_doc.metadata.get("content_hash", "")
                if not content_hash:
                    content_hash = self._content_fingerprint(lc_doc.page_content)

                chunk_payload = self._chunk_map.get(content_hash)
                if chunk_payload is None:
                    logger.warning(
                        "BM25RetrieverService: No ChunkPayload found for content_hash='%s' "
                        "(rank=%d). Skipping this BM25 result.",
                        content_hash[:16], rank,
                    )
                    continue

                # Normalize BM25 score: use inverse rank as proxy score
                # BM25Retriever doesn't expose raw BM25 scores, so we use
                # a rank-based normalization: score = (total - rank) / total
                normalized_score = round((total_results - rank) / total_results, 4)

                search_results.append(
                    SearchResult(document=chunk_payload, score=normalized_score)
                )

            logger.info(
                "BM25RetrieverService: BM25 search completed | "
                "query='%s' returned=%d matched=%d",
                query, total_results, len(search_results),
            )
            return SearchResponse(results=search_results)

        except Exception as e:
            logger.error(
                "BM25RetrieverService: Error during BM25 search for query='%s': %s",
                query, str(e),
                exc_info=True,
            )
            return SearchResponse(results=[])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _content_fingerprint(text: str) -> str:
        """Generate a stable fingerprint for chunk content lookup."""
        normalized = " ".join(text.split()).lower()
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()
