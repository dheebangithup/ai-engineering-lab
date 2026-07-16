from knowledge_hub.app.config import app_logger
from knowledge_hub.app.database.vector_store import VectorStore
from knowledge_hub.app.model import SearchResponse, SearchRequest
from knowledge_hub.app.model.api_reponse import ApiResponse, ResponseBuilder
from knowledge_hub.app.service.document_metadata_service import DocumentMetaDataService


class RetrievalService:
    def __init__(self, document_metadata_service: DocumentMetaDataService, vector_store: VectorStore):
        self.__metadata_service = document_metadata_service
        self.__vector_store = vector_store

    def search(self, option: SearchRequest) -> ApiResponse[SearchResponse] | ApiResponse[None]:
        try:
            app_logger.info(f"RetrievalService: Performing search for query: '{option.query}' with top_k={option.top_k}")
            candidates = self.__vector_store.search(option)
            app_logger.info("RetrievalService: Search completed successfully.")
            return ResponseBuilder.success(candidates, 'success')
        except Exception as e:
            app_logger.error("RetrievalService: Exception occurred in retrieval process", exc_info=True)
            return ResponseBuilder.failure(str(e))



