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
    def upsert(self, documents: list[EmbeddedDocument]) -> None:
        try:
            if not documents or len(documents)==0:
                app_logger.info("QdrantStore: Received empty list of documents to upsert. Skipping upsert operation.")
                return
            
            app_logger.info(f"QdrantStore: Preparing to upsert {len(documents)} points to collection '{app_settings.COLLECTION_NAME}'")
            points = list(map(lambda d: DocumentUtil.to_point(d), documents))
            self.__client.upsert(collection_name=app_settings.COLLECTION_NAME, points=points)
            app_logger.info(f"QdrantStore: Successfully upserted {len(documents)} points.")
        except Exception as e:
            app_logger.error("QdrantStore: Error upserting documents to Qdrant", exc_info=True)
            raise e

    @override
    def search(self, request: SearchRequest) -> SearchResponse:
        try:
            app_logger.info(f"QdrantStore: Executing search query='{request.query}' top_k={request.top_k} score_threshold={request.score_threshold}")
            query_vector = self.__embedding_provider.embed_query(request.query)

            # Build metadata filter from request.filters using only indexed fields
            qdrant_filter = None
            if request.filters:
                must_conditions = []
                allowed_fields = app_settings.INDEXED_PAYLOAD_FIELDS
                from qdrant_client.http import models

                for key, value in request.filters.items():
                    if value is None or value == "":
                        continue

                    if key not in allowed_fields:
                        app_logger.warning(
                            f"QdrantStore: Filter key '{key}' is not in configured INDEXED_PAYLOAD_FIELDS ({list(allowed_fields.keys())}). Skipping unindexed filter field."
                        )
                        continue

                    if isinstance(value, list):
                        must_conditions.append(
                            models.FieldCondition(
                                key=key,
                                match=models.MatchAny(any=[str(v) for v in value]),
                            )
                        )
                    else:
                        must_conditions.append(
                            models.FieldCondition(
                                key=key,
                                match=models.MatchValue(value=value if isinstance(value, (int, float, bool)) else str(value)),
                            )
                        )

                if must_conditions:
                    qdrant_filter = models.Filter(must=must_conditions)
                    app_logger.info(f"QdrantStore: Applied metadata query filter for keys: {[c.key for c in must_conditions]}")

            # Execute query_points with vector, filter, limit, and score threshold
            response = self.__client.query_points(
                collection_name=app_settings.COLLECTION_NAME,
                query=query_vector,
                query_filter=qdrant_filter,
                score_threshold=request.score_threshold if request.score_threshold is not None else None,
                limit=request.top_k,
            )

            if response.points is None or len(response.points) == 0:
                app_logger.info(f"QdrantStore: No search results found matching query and filters.")
                return SearchResponse(results=[])

            docs = []
            for doc in response.points:
                docs.append(
                    SearchResult(document=ChunkPayload.from_dict(doc.payload), score=doc.score)
                )
            app_logger.info(f"QdrantStore: Search completed successfully. Found {len(docs)} matching vector candidates.")
            return SearchResponse(results=docs)

        except Exception as e:
            app_logger.error(f"QdrantStore: Error executing search query: {str(e)}", exc_info=True)
            raise e

    @override
    def delete(self, chunk_ids: list[str]) -> None:
        try:
            if not chunk_ids:
                app_logger.info("QdrantStore: No chunk IDs provided for deletion. Skipping delete operation.")
                return
            
            app_logger.info(f"QdrantStore: Attempting to delete {len(chunk_ids)} points from collection '{app_settings.COLLECTION_NAME}'")
            
            from qdrant_client.http import models
            self.__client.delete(
                collection_name=app_settings.COLLECTION_NAME,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="chunk_id",
                                match=models.MatchAny(any=[str(cid) for cid in chunk_ids]),
                            ),
                        ]
                    )
                ),
            )
            app_logger.info("QdrantStore: Successfully deleted points from Qdrant.")
        except Exception as e:
            app_logger.error("QdrantStore: Error deleting points from Qdrant", exc_info=True)
            raise e

    def delete_by_document(self, document_id: str) -> None:
        try:
            app_logger.info(f"QdrantStore: Deleting all points for document_id '{document_id}' from collection '{app_settings.COLLECTION_NAME}'")
            from qdrant_client.http import models
            self.__client.delete(
                collection_name=app_settings.COLLECTION_NAME,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="document_id",
                                match=models.MatchValue(value=str(document_id)),
                            ),
                        ]
                    )
                ),
            )
            app_logger.info("QdrantStore: Successfully deleted all points for document_id from Qdrant.")
        except Exception as e:
            app_logger.error(f"QdrantStore: Error deleting points for document_id '{document_id}' from Qdrant", exc_info=True)
            raise e

    @override
    def update_payload_by_document(self, document_id: str, payload: dict) -> None:
        try:
            if not document_id:
                app_logger.error("QdrantStore: Validation failed - document_id is missing or empty for payload update.")
                raise ValueError("document_id must be provided for payload update.")
            if not payload:
                app_logger.warning("QdrantStore: Empty payload dict provided for payload update. Skipping operation.")
                return

            app_logger.info(f"QdrantStore: Bulk updating payload for document_id '{document_id}' in collection '{app_settings.COLLECTION_NAME}' with payload: {payload}")
            from qdrant_client.http import models
            self.__client.set_payload(
                collection_name=app_settings.COLLECTION_NAME,
                payload=payload,
                points=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="document_id",
                                match=models.MatchValue(value=str(document_id)),
                            ),
                        ]
                    )
                ),
            )
            app_logger.info(f"QdrantStore: Successfully updated payload in Qdrant for document_id '{document_id}'.")
        except Exception as e:
            app_logger.error(f"QdrantStore: Error updating payload for document_id '{document_id}' in Qdrant: {str(e)}", exc_info=True)
            raise e

    def _ensure_collection(self) -> None:
        """
        Ensures the Qdrant collection exists and payload indexes are created for all configured fields.
        """
        collection_name = app_settings.COLLECTION_NAME
        expected_dimension = self.__embedding_provider.dimension

        if not self.__client.collection_exists(collection_name):
            app_logger.info(f"QdrantStore: Creating collection '{collection_name}' with dimension={expected_dimension}")
            self.__client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=expected_dimension,
                    distance=Distance.COSINE,
                ),
            )

        # Check dimension compatibility if collection exists
        collection = self.__client.get_collection(collection_name)
        actual_dimension = collection.config.params.vectors.size
        if actual_dimension != expected_dimension:
            raise RuntimeError(
                f"Embedding dimension mismatch. "
                f"Collection={actual_dimension}, "
                f"Embedding Model={expected_dimension}"
            )

        # Ensure payload indexes ONLY for configured fields that are not yet indexed in Qdrant
        existing_indexes = set(collection.payload_schema.keys()) if collection.payload_schema else set()
        app_logger.debug(f"QdrantStore: Existing payload indexes in Qdrant: {list(existing_indexes)}")

        for field_name, schema_type in app_settings.INDEXED_PAYLOAD_FIELDS.items():
            if field_name in existing_indexes:
                app_logger.debug(f"QdrantStore: Payload index for field '{field_name}' already exists in Qdrant. Skipping creation.")
                continue

            try:
                app_logger.info(f"QdrantStore: Payload index missing for field '{field_name}'. Creating {schema_type} index in Qdrant...")
                s_type = PayloadSchemaType.INTEGER if schema_type == "integer" else PayloadSchemaType.KEYWORD
                self.__client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=s_type,
                )
                app_logger.info(f"QdrantStore: Payload index successfully created for field '{field_name}' ({schema_type}).")
            except Exception as ie:
                app_logger.warning(f"QdrantStore: Notice while creating payload index for field '{field_name}': {ie}")

    @override
    def scroll_all_payloads(self, batch_size: int = 100) -> list[dict]:
        """
        Scrolls through all points in the Qdrant collection and returns their payloads.
        Uses Qdrant scroll API with with_vectors=False for efficiency.
        Used by BM25RetrieverService to build the keyword search index from stored chunk content.
        """
        try:
            app_logger.info(
                f"QdrantStore: Starting scroll_all_payloads for collection '{app_settings.COLLECTION_NAME}' "
                f"with batch_size={batch_size}"
            )
            all_payloads = []
            offset = None
            batch_count = 0

            while True:
                points, next_offset = self.__client.scroll(
                    collection_name=app_settings.COLLECTION_NAME,
                    limit=batch_size,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )

                if not points:
                    app_logger.debug("QdrantStore: scroll_all_payloads received empty batch. Scroll complete.")
                    break

                batch_count += 1
                for point in points:
                    if point.payload:
                        all_payloads.append(point.payload)

                app_logger.debug(
                    f"QdrantStore: scroll_all_payloads batch {batch_count} fetched {len(points)} points "
                    f"(total payloads so far: {len(all_payloads)})"
                )

                if next_offset is None:
                    break
                offset = next_offset

            app_logger.info(
                f"QdrantStore: scroll_all_payloads completed. Retrieved {len(all_payloads)} payloads "
                f"across {batch_count} batches from collection '{app_settings.COLLECTION_NAME}'."
            )
            return all_payloads

        except Exception as e:
            app_logger.error(
                f"QdrantStore: Error during scroll_all_payloads for collection "
                f"'{app_settings.COLLECTION_NAME}': {str(e)}",
                exc_info=True,
            )
            raise e
