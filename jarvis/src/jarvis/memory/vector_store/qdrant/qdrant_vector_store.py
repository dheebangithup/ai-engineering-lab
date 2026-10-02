from typing import Any
from uuid import UUID, uuid5

from qdrant_client import QdrantClient, models
from qdrant_client.models import (
    Distance,
    PointStruct,
    SparseVector as QdrantSparseVector,
    SparseVectorParams,
    VectorParams,
)

from jarvis.workspace import Workspace, default_workspace

from ..enums import RetrievalMode
from ..vector_store import VectorStore
from ..models import SearchRequest, SearchResult, SparseVector


class QdrantVectorStore(VectorStore):
    """
    Qdrant implementation of the JARVIS VectorStore interface.
    """

    DENSE_VECTOR_NAME = "dense"
    SPARSE_VECTOR_NAME = "sparse"

    _UUID_NAMESPACE = UUID(
        "7f2f7e0e-7f6a-4d8d-8b9e-3e6b2f0a9c01"
    )

    def __init__(
        self,
        workspace: Workspace | None = None,
        collection_name: str = "memories",
        vector_size: int = 1024,
    ):
        self.workspace = workspace or default_workspace()

        self.workspace.initialize()

        self.collection_name = collection_name
        self.vector_size = vector_size

        self.client = QdrantClient(
            path=str(self.workspace.qdrant_dir)
        )

        self._ensure_collection()

    # ------------------------------------------------------------------
    # Collection
    # ------------------------------------------------------------------

    def _ensure_collection(self) -> None:
        if self.client.collection_exists(self.collection_name):
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config={
                self.DENSE_VECTOR_NAME: VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                )
            },
            sparse_vectors_config={
                self.SPARSE_VECTOR_NAME: SparseVectorParams(
                    index=models.SparseIndexParams(
                        on_disk=False
                    )
                )
            },
        )

    # ------------------------------------------------------------------
    # Point ID
    # ------------------------------------------------------------------

    def _point_id(self, memory_id: str) -> str:
        """
        Convert arbitrary JARVIS memory IDs into deterministic UUIDs.

        Qdrant point IDs are represented as UUIDs or unsigned integers.
        JARVIS keeps the original memory_id in the payload.
        """

        return str(
            uuid5(
                self._UUID_NAMESPACE,
                memory_id,
            )
        )

    # ------------------------------------------------------------------
    # Add
    # ------------------------------------------------------------------

    def add(
        self,
        memory_id: str,
        dense_vector: list[float],
        sparse_vector: SparseVector,
        payload: dict[str, Any],
    ) -> None:

        if not dense_vector:
            raise ValueError("dense_vector cannot be empty")

        if sparse_vector is None:
            raise ValueError("sparse_vector is required")

        point_payload = {
            **payload,
            "memory_id": memory_id,
        }

        point = PointStruct(
            id=self._point_id(memory_id),
            vector={
                self.DENSE_VECTOR_NAME: dense_vector,
                self.SPARSE_VECTOR_NAME: QdrantSparseVector(
                    indices=sparse_vector.indices,
                    values=sparse_vector.values,
                ),
            },
            payload=point_payload,
        )

        self.client.upsert(
            collection_name=self.collection_name,
            points=[point],
        )

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(
        self,
        memory_id: str,
        dense_vector: list[float] | None = None,
        sparse_vector: SparseVector | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:

        point_id = self._point_id(memory_id)

        if dense_vector is not None:
            self.client.update_vectors(
                collection_name=self.collection_name,
                points=[
                    models.PointVectors(
                        id=point_id,
                        vector={
                            self.DENSE_VECTOR_NAME: dense_vector,
                        },
                    )
                ],
            )

        if sparse_vector is not None:
            self.client.update_vectors(
                collection_name=self.collection_name,
                points=[
                    models.PointVectors(
                        id=point_id,
                        vector={
                            self.SPARSE_VECTOR_NAME: QdrantSparseVector(
                                indices=sparse_vector.indices,
                                values=sparse_vector.values,
                            ),
                        },
                    )
                ],
            )

        if payload is not None:
            self.client.set_payload(
                collection_name=self.collection_name,
                payload={
                    **payload,
                    "memory_id": memory_id,
                },
                points=[point_id],
            )

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete(
        self,
        memory_id: str,
    ) -> None:

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(
                points=[
                    self._point_id(memory_id)
                ]
            ),
        )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        request: SearchRequest,
    ) -> list[SearchResult]:

        query_filter = self._build_filter(request.filter)

        if request.mode == RetrievalMode.DENSE:
            return self._dense_search(
                request,
                query_filter,
            )

        if request.mode == RetrievalMode.SPARSE:
            return self._sparse_search(
                request,
                query_filter,
            )

        if request.mode == RetrievalMode.HYBRID:
            return self._hybrid_search(
                request,
                query_filter,
            )

        raise ValueError(
            f"Unsupported retrieval mode: {request.mode}"
        )

    # ------------------------------------------------------------------
    # Dense search
    # ------------------------------------------------------------------

    def _dense_search(
        self,
        request: SearchRequest,
        query_filter: models.Filter | None,
    ) -> list[SearchResult]:

        if request.dense_vector is None:
            raise ValueError(
                "dense_vector is required for dense search"
            )

        response = self.client.query_points(
            collection_name=self.collection_name,
            query=request.dense_vector,
            using=self.DENSE_VECTOR_NAME,
            query_filter=query_filter,
            limit=request.limit,
            with_payload=True,
        )

        return self._map_results(response.points)

    # ------------------------------------------------------------------
    # Sparse search
    # ------------------------------------------------------------------

    def _sparse_search(
        self,
        request: SearchRequest,
        query_filter: models.Filter | None,
    ) -> list[SearchResult]:

        if request.sparse_vector is None:
            raise ValueError(
                "sparse_vector is required for sparse search"
            )

        query = QdrantSparseVector(
            indices=request.sparse_vector.indices,
            values=request.sparse_vector.values,
        )

        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query,
            using=self.SPARSE_VECTOR_NAME,
            query_filter=query_filter,
            limit=request.limit,
            with_payload=True,
        )

        return self._map_results(response.points)

    # ------------------------------------------------------------------
    # Hybrid search
    # ------------------------------------------------------------------

    def _hybrid_search(
        self,
        request: SearchRequest,
        query_filter: models.Filter | None,
    ) -> list[SearchResult]:

        if request.dense_vector is None:
            raise ValueError(
                "dense_vector is required for hybrid search"
            )

        if request.sparse_vector is None:
            raise ValueError(
                "sparse_vector is required for hybrid search"
            )

        dense_prefetch = models.Prefetch(
            query=request.dense_vector,
            using=self.DENSE_VECTOR_NAME,
            limit=request.prefetch_limit,
        )

        sparse_prefetch = models.Prefetch(
            query=QdrantSparseVector(
                indices=request.sparse_vector.indices,
                values=request.sparse_vector.values,
            ),
            using=self.SPARSE_VECTOR_NAME,
            limit=request.prefetch_limit,
        )

        response = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                dense_prefetch,
                sparse_prefetch,
            ],
            query=models.FusionQuery(
                fusion=models.Fusion.RRF
            ),
            query_filter=query_filter,
            limit=request.limit,
            with_payload=True,
        )

        return self._map_results(response.points)

    # ------------------------------------------------------------------
    # Payload filtering
    # ------------------------------------------------------------------

    def _build_filter(
        self,
        filters: dict[str, Any] | None,
    ) -> models.Filter | None:

        if not filters:
            return None

        conditions = []

        for field, value in filters.items():

            if isinstance(value, list):
                condition = models.FieldCondition(
                    key=field,
                    match=models.MatchAny(
                        any=value
                    ),
                )
            else:
                condition = models.FieldCondition(
                    key=field,
                    match=models.MatchValue(
                        value=value
                    ),
                )

            conditions.append(condition)

        return models.Filter(
            must=conditions
        )

    # ------------------------------------------------------------------
    # Result mapping
    # ------------------------------------------------------------------

    def _map_results(
        self,
        points: list[Any],
    ) -> list[SearchResult]:

        results = []

        for point in points:

            payload = point.payload or {}

            memory_id = payload.get(
                "memory_id"
            )

            if memory_id is None:
                continue

            results.append(
                SearchResult(
                    memory_id=memory_id,
                    score=float(point.score),
                    payload=payload,
                )
            )

        return results