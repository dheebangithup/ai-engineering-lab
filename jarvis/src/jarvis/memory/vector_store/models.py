from dataclasses import dataclass, field
from typing import Any

from .enums import RetrievalMode


@dataclass(frozen=True)
class SparseVector:
    indices: list[int]
    values: list[float]


@dataclass(frozen=True)
class SearchRequest:
    mode: RetrievalMode

    dense_vector: list[float] | None = None
    sparse_vector: SparseVector | None = None

    limit: int = 10
    filter: dict[str, Any] | None = None

    prefetch_limit: int = 20


@dataclass(frozen=True)
class SearchResult:
    memory_id: str
    score: float
    payload: dict[str, Any] = field(default_factory=dict)