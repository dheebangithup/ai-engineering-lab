"""
Tool Discovery Engine for J.A.R.V.I.S.
Ranks tools using BM25Okapi over tool names, descriptions, and parameter schemas.
Allows agents to discover relevant tools from a registry of thousands using natural language.
"""

import re
from typing import List, Optional
from rank_bm25 import BM25Okapi
from jarvis.logger import get_logger
from jarvis.tools.schemas import ToolDefinition
from jarvis.tools.tool_registry import ToolRegistry

logger = get_logger("tools.discovery")


class ToolDiscovery:
    """Natural-language search over the ToolRegistry using BM25Okapi."""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self._bm25: Optional[BM25Okapi] = None
        self._indexed_tool_ids: List[str] = []
        self._last_count = -1

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into alphanumeric lowercase tokens (splitting on underscores and spaces)."""
        clean_text = text.replace("_", " ").lower()
        return [w for w in re.findall(r"[a-z0-9]+", clean_text) if len(w) > 1]

    def _build_index_if_needed(self) -> None:
        """Re-index tools if the registry size changed."""
        current_count = len(self.registry)
        if self._bm25 is not None and self._last_count == current_count:
            return

        tools = self.registry.list_tools()
        if not tools:
            self._bm25 = None
            self._indexed_tool_ids = []
            self._last_count = 0
            return

        corpus = []
        self._indexed_tool_ids = []
        for tool in tools:
            # Emphasize tool_id and name by weighting them in the BM25 token stream
            param_names = " ".join(tool.parameters.keys())
            doc_text = f"{tool.tool_id} {tool.tool_id} {tool.name} {tool.name} {tool.category} {tool.description} {param_names}"
            corpus.append(self._tokenize(doc_text))
            self._indexed_tool_ids.append(tool.tool_id)

        self._bm25 = BM25Okapi(corpus)
        self._last_count = current_count
        logger.debug(f"Built BM25 tool index with {len(self._indexed_tool_ids)} tools")

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        max_results: int = 5,
        min_score: float = 0.1,
    ) -> List[ToolDefinition]:
        """
        Search and rank tools relevant to the query.
        Returns top-K matching ToolDefinition objects.
        """
        self._build_index_if_needed()
        if not self._bm25 or not self._indexed_tool_ids:
            return []

        tokens = self._tokenize(query)
        if not tokens:
            return []

        scores = self._bm25.get_scores(tokens)

        # Pair tool_id with score + keyword bonus
        scored_tools = []
        token_set = set(tokens)
        for tool_id, bm25_score in zip(self._indexed_tool_ids, scores):
            tool_def = self.registry.get_definition(tool_id)
            if not tool_def:
                continue
            if category and tool_def.category.lower() != category.lower():
                continue

            # Exact keyword overlap boost for tool_id and name
            id_tokens = set(self._tokenize(f"{tool_def.tool_id} {tool_def.name}"))
            overlap = len(token_set.intersection(id_tokens))
            final_score = bm25_score + (overlap * 2.0)

            scored_tools.append((final_score, tool_def))

        # Sort descending by score
        scored_tools.sort(key=lambda x: x[0], reverse=True)
        results = [t[1] for t in scored_tools[:max_results]]

        logger.debug(f"Search for '{query}' returned {len(results)} tools (top: {[t.tool_id for t in results]})")
        return results
