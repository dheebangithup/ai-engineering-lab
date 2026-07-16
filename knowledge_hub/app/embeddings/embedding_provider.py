from abc import ABC, abstractmethod
from knowledge_hub.app.model import Document
from knowledge_hub.app.model import EmbeddedDocument


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self,chunks:list[Document])->list[EmbeddedDocument]:
        pass

    @abstractmethod
    def embed_query(self, query: str) -> list[float]:
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        pass