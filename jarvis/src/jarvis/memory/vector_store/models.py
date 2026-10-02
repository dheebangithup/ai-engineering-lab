from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SearchResult:
    memory_id: str
    score: float
    payload: dict[str, Any]