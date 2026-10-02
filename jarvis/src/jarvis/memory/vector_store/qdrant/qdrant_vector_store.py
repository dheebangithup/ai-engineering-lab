from typing import Any

from qdrant_client import QdrantClient

from ..enums import RetrievalMode
from ..vector_store import VectorStore
from ..models import SearchResult
from jarvis.workspace import Workspace, default_workspace


class QdrantVectorStore(VectorStore):

    def __init__(
        self,
        workspace: Workspace | None = None,
        collection_name: str="memories",
        vector_size: int=1024,
    ):
        self.workspace = workspace or default_workspace()

        self.client = QdrantClient(
            path=str(self.workspace.qdrant_dir)
        )
        self.collection_name = collection_name
        self.vector_size = vector_size

    def add(
        self,
        memory_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        raise NotImplementedError

    def delete(
        self,
        memory_id: str,
    ) -> None:
        raise NotImplementedError

    def search(
        self,
        query_vector: list[float],
        mode: RetrievalMode = RetrievalMode.DENSE,
        limit: int = 10,
    ) -> list[SearchResult]:
        raise NotImplementedError