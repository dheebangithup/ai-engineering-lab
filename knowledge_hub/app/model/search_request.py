from pydantic.dataclasses import dataclass


@dataclass
class SearchRequest:
    query: str
    top_k: int = 5
    filters: dict | None = None