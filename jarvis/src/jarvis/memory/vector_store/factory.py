from enum import Enum

from jarvis.workspace import Workspace

from .vector_store import VectorStore
from .qdrant import QdrantVectorStore


class VectorStoreType(Enum):
    QDRANT = "qdrant"


class VectorStoreFactory:

    @staticmethod
    def create(
        store_type: VectorStoreType,
        *,
        workspace: Workspace,
        collection_name: str = "memories",
        vector_size: int = 1024,
    ) -> VectorStore:

        if store_type == VectorStoreType.QDRANT:
            return QdrantVectorStore(
                workspace=workspace,
                collection_name=collection_name,
                vector_size=vector_size,
            )

        raise ValueError(
            f"Unsupported vector store type: {store_type}"
        )