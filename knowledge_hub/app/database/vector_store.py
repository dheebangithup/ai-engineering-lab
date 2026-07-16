from abc import ABC, abstractmethod

from knowledge_hub.app.model import EmbeddedDocument, SearchRequest, SearchResponse


class VectorStore(ABC):
    """
    Abstract class for vector store.

    Indexing files in vector store for metadata filtering
     -document_id
     - chunk_id
     - page_number
    """
    @abstractmethod
    def upsert(
        self,
        documents: list[EmbeddedDocument],
    ) -> None:
        """
        Insert or update vectors.
        """
        pass

    @abstractmethod
    def search(
        self,
        request: SearchRequest,
    ) -> SearchResponse:
        """
        Perform similarity search.
        """
        pass