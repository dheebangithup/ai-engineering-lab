from knowledge_hub.app.entity import DocumentMetaDataEntity,ChunkMetaDataEntity
from knowledge_hub.app.repositories import DocumentMetaDataRepository
from knowledge_hub.app.repositories.chunk_metadata_repository import ChunkMetaDataRepository
from knowledge_hub.app.config import app_logger



class DocumentMetaDataService:
    def __init__(self, doc_repo: DocumentMetaDataRepository, chunk_repo: ChunkMetaDataRepository):
        self.doc_repo = doc_repo
        self.chunk_repo = chunk_repo

    def create_doc(self, doc: DocumentMetaDataEntity)->DocumentMetaDataEntity:
        return self.doc_repo.save(doc)

    def create_doc_with_chunks(self, doc: DocumentMetaDataEntity, chunks: list[ChunkMetaDataEntity])->DocumentMetaDataEntity:
        saved_doc = self.doc_repo.save(doc)
        for chunk in chunks:
            chunk.document_id = saved_doc.document_id
        self.chunk_repo.save_all(chunks)
        return saved_doc

    def update_doc(self, doc: DocumentMetaDataEntity)->DocumentMetaDataEntity:
        return self.doc_repo.update(doc)

    def delete_chunks_for_doc(self, document_id: str):
        return self.chunk_repo.delete_by_document(document_id)

    def save_chunks(self, chunks: list[ChunkMetaDataEntity])->list[ChunkMetaDataEntity]:
        return self.chunk_repo.save_all(chunks)

    def get_doc(self, document_id: str)->DocumentMetaDataEntity:
        return self.doc_repo.find_by_document_id(document_id)

    def get_doc_by_hash(self, doc_hash: str)->DocumentMetaDataEntity:
        return self.doc_repo.find_by_hash(doc_hash)

    def get_all_docs(self) -> list[DocumentMetaDataEntity]:
        try:
            app_logger.info("DocumentMetaDataService: Request received to fetch all document metadata entities.")
            docs = self.doc_repo.find_all()
            app_logger.info(f"DocumentMetaDataService: Successfully retrieved {len(docs)} documents.")
            return docs
        except Exception as e:
            app_logger.error(f"DocumentMetaDataService: Failed to fetch all documents: {str(e)}", exc_info=True)
            raise e

    def delete_doc_and_chunks(self, document_id: str):
        try:
            app_logger.info(f"DocumentMetaDataService: Request received to delete document and chunks for ID: {document_id}")
            self.chunk_repo.delete_by_document(document_id)
            deleted_doc = self.doc_repo.delete(document_id)
            app_logger.info(f"DocumentMetaDataService: Successfully deleted document and chunks for ID: {document_id}")
            return deleted_doc
        except Exception as e:
            app_logger.error(f"DocumentMetaDataService: Failed to delete document and chunks for ID {document_id}: {str(e)}", exc_info=True)
            raise e

    def get_chunks_for_doc(self, document_id: str)->list[ChunkMetaDataEntity]:
        return self.chunk_repo.find_by_document(document_id)

    def get_chunk_by_page(self, document_id: str, page_number: int)->list[ChunkMetaDataEntity]:
        return self.chunk_repo.find_by_page(document_id, page_number)

    def delete_chunk_by_page(self, document_id: str, page_number: int)->ChunkMetaDataEntity:
        return self.chunk_repo.delete_by_page(document_id, page_number)

    def update_chunk(self, chunk: ChunkMetaDataEntity) -> ChunkMetaDataEntity:
        try:
            app_logger.info(f"DocumentMetaDataService: Request received to update chunk metadata with ID: {chunk.chunk_id if chunk else 'None'}")
            if not chunk or chunk.chunk_id is None:
                app_logger.error("DocumentMetaDataService: Validation failed - chunk or chunk_id is missing.")
                raise ValueError("chunk and chunk_id must be provided.")
            
            updated_chunk = self.chunk_repo.update(chunk)
            app_logger.info(f"DocumentMetaDataService: Successfully updated chunk metadata with ID: {chunk.chunk_id}")
            return updated_chunk
        except Exception as e:
            app_logger.error(f"DocumentMetaDataService: Failed to update chunk metadata: {str(e)}", exc_info=True)
            raise e

    def update_chunks(self, chunks: list[ChunkMetaDataEntity]) -> list[ChunkMetaDataEntity]:
        try:
            app_logger.info(f"DocumentMetaDataService: Request received to bulk update {len(chunks)} chunk metadata records.")
            for index, chunk in enumerate(chunks):
                if not chunk or chunk.chunk_id is None:
                    app_logger.error(f"DocumentMetaDataService: Validation failed - chunk at index {index} is missing or has no chunk_id.")
                    raise ValueError(f"Each chunk must have a valid chunk_id. Error at index {index}.")
            
            updated_chunks = self.chunk_repo.update_all(chunks)
            app_logger.info(f"DocumentMetaDataService: Successfully bulk updated {len(chunks)} chunk metadata records.")
            return updated_chunks
        except Exception as e:
            app_logger.error(f"DocumentMetaDataService: Failed to bulk update chunk metadata: {str(e)}", exc_info=True)
            raise e

    def delete_chunks_by_ids(self, chunk_ids: list):
        try:
            app_logger.info(f"DocumentMetaDataService: Request received to delete {len(chunk_ids) if chunk_ids else 0} chunk metadata records.")
            self.chunk_repo.delete_by_ids(chunk_ids)
            app_logger.info("DocumentMetaDataService: Successfully processed deletion of chunk metadata records.")
        except Exception as e:
            app_logger.error(f"DocumentMetaDataService: Failed to delete chunk metadata: {str(e)}", exc_info=True)
            raise e

