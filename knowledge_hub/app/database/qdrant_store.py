from typing import override

from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance, PayloadSchemaType

from knowledge_hub.app.config import app_settings, app_logger
from knowledge_hub.app.database.vector_store import VectorStore
from knowledge_hub.app.embeddings.embedding_provider import EmbeddingProvider
from knowledge_hub.app.model import EmbeddedDocument, SearchRequest, SearchResponse, SearchResult
from knowledge_hub.app.model.chunk_payload import ChunkPayload
from knowledge_hub.app.utils.document_util import DocumentUtil


class QdrantStore(VectorStore):
    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        self.__client = QdrantClient(
            url=app_settings.QDRANT_URL,
            api_key=app_settings.QDRANT_API_KEY,
        )
        self.__embedding_provider = embedding_provider
        self._ensure_collection()

    @override
    def upsert(self, documents: list[EmbeddedDocument], ) -> None:
        try:
            self.__client.upsert(collection_name=app_settings.COLLECTION_NAME,
                                 points=list(map(lambda d: DocumentUtil.to_point(d), documents)))
        except Exception as e:
            app_logger.error("Error upserting documents to Qdrant", exc_info=True)
            raise e

    @override
    def search(self, request: SearchRequest) -> SearchResponse:
        query_vector = self.__embedding_provider.embed_query(request.query)
        response=self.__client.query_points(
            collection_name=app_settings.COLLECTION_NAME,
            query=query_vector,
            limit=request.top_k
        )
        if response.points is None:
            app_logger.warning(f"No search results for query: {request.query}")
            raise Exception(f"No search results for query: {request.query}")

        docs=[]
        for doc in response.points:
            docs.append(
                SearchResult(document=ChunkPayload.from_dict(doc.payload),score=doc.score)
            )
        app_logger.debug(f'search found {len(docs)} documents for query {request.query}')
        return SearchResponse(results=docs)

    def _ensure_collection(self) -> None:
        """
        Ensures the Qdrant collection exists and has the correct configuration.
        """

        collection_name = app_settings.COLLECTION_NAME
        expected_dimension = self.__embedding_provider.dimension

        if not self.__client.collection_exists(collection_name):
            self.__client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=expected_dimension,
                    distance=Distance.COSINE,
                ),
            )

            # Payload indexes (recommended)
            self.__client.create_payload_index(
                collection_name=collection_name,
                field_name="document_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )

            self.__client.create_payload_index(
                collection_name=collection_name,
                field_name="page_number",
                field_schema=PayloadSchemaType.INTEGER,
            )

            self.__client.create_payload_index(
                collection_name=collection_name,
                field_name="chunk_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )

            return

        # Collection already exists
        collection = self.__client.get_collection(collection_name)

        actual_dimension = collection.config.params.vectors.size

        if actual_dimension != expected_dimension:
            raise RuntimeError(
                f"Embedding dimension mismatch. "
                f"Collection={actual_dimension}, "
                f"Embedding Model={expected_dimension}"
            )
