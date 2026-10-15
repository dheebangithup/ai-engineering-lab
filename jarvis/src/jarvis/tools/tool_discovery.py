import re
from typing import List, Optional, Set

from rank_bm25 import BM25Okapi
from spacy.lang.en.stop_words import STOP_WORDS as DEFAULT_STOP_WORDS

from jarvis.tools.schemas import ToolDefinition
from jarvis.tools.tool_registry import ToolRegistry


def tokenize(text: str, stop_words: Optional[Set[str]] = None) -> List[str]:
    """
    Split text into normalized alphanumeric tokens.
    Filters out common stop words using spaCy's standard English stop words by default.
    """
    stops = stop_words if stop_words is not None else DEFAULT_STOP_WORDS
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [t for t in tokens if t not in stops and len(t) > 1]


class ToolDiscovery:
    """
    Discovers relevant tools using BM25Okapi ranking against tool names and descriptions.
    Powered by rank-bm25 for exact saturation/normalization and spaCy for standard stop words.
    Returns only tool definitions, preserving separation from implementations.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        k1: float = 1.5,
        b: float = 0.75,
        epsilon: float = 0.25,
        stop_words: Optional[Set[str]] = None,
    ) -> None:
        self._registry = registry
        self._k1 = k1
        self._b = b
        self._epsilon = epsilon
        self._stop_words = stop_words if stop_words is not None else DEFAULT_STOP_WORDS

    def _build_doc_tokens(self, tool_def: ToolDefinition) -> List[str]:
        """
        Build tokens for a tool definition.
        Gives additional weight to tool ID and name tokens.
        """
        id_tokens = tokenize(tool_def.id, self._stop_words)
        name_tokens = tokenize(tool_def.name, self._stop_words)
        desc_tokens = tokenize(tool_def.description, self._stop_words)

        tokens = id_tokens * 3 + name_tokens * 2 + desc_tokens
        return tokens if tokens else ["tool"]

    def discover(
        self,
        query: str,
        max_results: int = 5,
    ) -> List[ToolDefinition]:
        """
        Find relevant tools matching the natural-language query using BM25Okapi.
        Returns top `max_results` matching ToolDefinitions, or an empty list if no match.
        """
        query_tokens = tokenize(query, self._stop_words)
        if not query_tokens:
            return []

        all_tools = self._registry.list_definitions()
        if not all_tools:
            return []

        tokenized_corpus = [self._build_doc_tokens(t) for t in all_tools]

        bm25 = BM25Okapi(
            tokenized_corpus,
            k1=self._k1,
            b=self._b,
            epsilon=self._epsilon,
        )

        doc_scores = bm25.get_scores(query_tokens)

        scored_tools: List[tuple[float, ToolDefinition]] = []
        for score, tool_def, doc_tokens in zip(doc_scores, all_tools, tokenized_corpus):
            has_term_overlap = any(term in doc_tokens for term in query_tokens)
            if score > 0.0 and has_term_overlap:
                scored_tools.append((float(score), tool_def))

        scored_tools.sort(key=lambda item: item[0], reverse=True)

        return [tool_def for _, tool_def in scored_tools[:max_results]]
