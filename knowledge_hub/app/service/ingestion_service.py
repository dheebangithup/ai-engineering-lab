
from knowledge_hub.app.config import app_logger
from knowledge_hub.app.database.vector_store import VectorStore
from knowledge_hub.app.embeddings.embedding_provider import EmbeddingProvider
from knowledge_hub.app.entity import DocumentMetaDataEntity, ChunkMetaDataEntity
from knowledge_hub.app.enums import FileType
from knowledge_hub.app.processor.document_processor import DocumentProcessor
from knowledge_hub.app.service.document_metadata_service import DocumentMetaDataService
from knowledge_hub.app.utils.hash_util import HashUtil


class IngestionService:
    """
    IngestionService

    ├── Generate document_id
    ├── Calculate file hash
    ├── Check duplicate
    ├── Parse
    ├── Compare page hash
    ├── Delete changed page vectors
    ├── Chunk
    ├── Generate chunk IDs
    ├── Generate chunk hash
    ├── Save metadata
    ├── Embed
    ├── Upsert to Qdrant
    └── Update status
    """

    def __init__(
            self,
            processor: DocumentProcessor,
            embedding_provider: EmbeddingProvider,
            vector_store: VectorStore,
            meta_data_service: DocumentMetaDataService,
    ):
        self.processor = processor
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.meta_data_service = meta_data_service

    def ingest(self, file_path: str, file_type: FileType):
        doc_meta = None
        import uuid
        try:
            app_logger.info(f"IngestionService: Starting ingestion pipeline for file '{file_path}' (type={file_type.value})")

            doc_hash = HashUtil.generate_file_hash(file_path)
            app_logger.info(f"IngestionService: Generated file hash '{doc_hash}'")

            doc_meta = self.meta_data_service.get_doc_by_hash(doc_hash)
            if doc_meta is not None:
                app_logger.info(f"IngestionService: Duplicate document found (hash={doc_hash}). Clearing existing metadata and chunks (document_id={doc_meta.document_id}).")
                # Delete old chunks metadata first
                self.meta_data_service.delete_chunks_for_doc(doc_meta.document_id)
                doc_meta.status = "PROCESSING"
                self.meta_data_service.update_doc(doc_meta)
            else:
                file_name = file_path.split("/")[-1] if "/" in file_path else file_path.split("\\")[-1]
                app_logger.info(f"IngestionService: New file '{file_name}' detected. Creating metadata record.")
                doc_meta = DocumentMetaDataEntity(
                    file_name=file_name,
                    file_hash=doc_hash,
                    file_type=file_type.value,
                    status="PROCESSING"
                )
                self.meta_data_service.create_doc(doc_meta)
                app_logger.info(f"IngestionService: Document metadata created in DB with ID: {doc_meta.document_id}")

            app_logger.info(f"IngestionService: Invoking document processor '{self.processor.__class__.__name__}'")
            documents = self.processor.process(file_path, doc_meta)
            
            # Update total pages and other info in metadata DB
            self.meta_data_service.update_doc(doc_meta)
            app_logger.info(f"IngestionService: Document processing completed. Generated {len(documents)} chunks.")

            app_logger.info("IngestionService: Commencing chunk embedding generation.")
            embedded_chunks = self.embedding_provider.embed(documents)
            app_logger.info(f"IngestionService: Embedding phase completed. Embedded {len(embedded_chunks)} chunks.")

            app_logger.info("IngestionService: Upserting embedded chunks into vector store.")
            self.vector_store.upsert(embedded_chunks)
            app_logger.info("IngestionService: Vector store upsert completed successfully.")
            
            # Save chunks metadata to relational database
            app_logger.info("IngestionService: Saving chunk metadata entities to relational database.")
            chunk_entities = []
            for chunk in documents:
                chunk_entities.append(ChunkMetaDataEntity(
                    chunk_id=uuid.UUID(chunk.metadata.chunk_id),
                    document_id=doc_meta.document_id,
                    page_number=chunk.metadata.page_number if chunk.metadata.page_number is not None else 1,
                    chunk_hash=HashUtil.generate_chunk_hash(chunk.content),
                    vector_id=chunk.metadata.chunk_id
                ))
            self.meta_data_service.save_chunks(chunk_entities)
            app_logger.info(f"IngestionService: Successfully saved {len(chunk_entities)} chunk metadata records to relational database.")
            
            doc_meta.status = "SUCCESS"
            self.meta_data_service.update_doc(doc_meta)
            app_logger.info(f"IngestionService: Ingestion pipeline completed successfully for document_id={doc_meta.document_id}")
            return doc_meta

        except Exception as e:
            app_logger.error(f"IngestionService: Critical error during ingestion pipeline execution for file '{file_path}'", exc_info=True)
            if doc_meta is not None:
                try:
                    doc_meta.status = "FAILED"
                    self.meta_data_service.update_doc(doc_meta)
                    app_logger.info(f"IngestionService: Updated document_id={doc_meta.document_id} status to 'FAILED'.")
                except Exception as db_err:
                    app_logger.error(f"IngestionService: Failed to update document status to 'FAILED': {db_err}", exc_info=True)
            raise e



