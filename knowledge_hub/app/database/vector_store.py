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

    @abstractmethod
    def delete(
        self,
        chunk_ids: list[str],
    ) -> None:
        """
        Delete vectors by chunk_ids.
        """
        pass

    @abstractmethod
    def delete_by_document(
        self,
        document_id: str,
    ) -> None:
        """
        Delete all vectors for a document.
        """
        pass

    @abstractmethod
    def update_payload_by_document(
        self,
        document_id: str,
        payload: dict,
    ) -> None:
        """
        Bulk-update metadata payload for all vectors of a document.
        """
        pass

    @abstractmethod
    def scroll_all_payloads(self, batch_size: int = 100) -> list[dict]:
        """
        Scroll through all points in the collection and return their payloads.
        Used by BM25RetrieverService to build the keyword search index.
        """
        pass