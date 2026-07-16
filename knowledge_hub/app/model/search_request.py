from pydantic.dataclasses import dataclass


@dataclass
class SearchRequest:
    query: str
    top_k: int = 5
    score_threshold: float = 0.7
    max_context_tokens: int = 6000
    filters: dict | None = None
