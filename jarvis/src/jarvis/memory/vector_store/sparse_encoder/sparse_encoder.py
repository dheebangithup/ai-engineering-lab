from abc import ABC, abstractmethod

from qdrant_client.models import SparseVector


class SparseEncoder(ABC):

    @abstractmethod
    def encode(self, text: str) -> SparseVector:
        """Encode text into a sparse vector."""
        raise NotImplementedError

    @abstractmethod
    def encode_batch(
        self,
        texts: list[str],
    ) -> list[SparseVector]:
        """Encode multiple texts into sparse vectors."""
        raise NotImplementedError