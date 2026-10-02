from abc import ABC, abstractmethod
from typing import Any

from .enums import RetrievalMode
from .models import SearchResult


class VectorStore(ABC):

    @abstractmethod
    def add(
        self,
        memory_id: str,
        vector: list[float],
        payload: dict[str, Any],
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
        query_vector: list[float],
        mode: RetrievalMode = RetrievalMode.DENSE,
        limit: int = 10,
    ) -> list[SearchResult]:
        pass