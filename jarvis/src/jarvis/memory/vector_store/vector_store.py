from abc import ABC, abstractmethod
from typing import Any

from .models import SearchRequest, SearchResult


class VectorStore(ABC):

    @abstractmethod
    def add(
        self,
        memory_id: str,
        dense_vector: list[float],
        sparse_vector: Any,
        payload: dict[str, Any],
    ) -> None:
        pass

    @abstractmethod
    def update(
        self,
        memory_id: str,
        dense_vector: list[float] | None = None,
        sparse_vector: Any | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        pass

    @abstractmethod
    def delete(
        self,
        memory_id: str,
    ) -> None:
        pass

    @abstractmethod
    def search(
        self,
        request: SearchRequest,
    ) -> list[SearchResult]:
        pass