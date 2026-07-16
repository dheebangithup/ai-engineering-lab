
from knowledge_hub.app.chunkers.chunker import Chunker
from knowledge_hub.app.config import app_logger
from knowledge_hub.app.database.vector_store import VectorStore
from knowledge_hub.app.embeddings.embedding_provider import EmbeddingProvider
from knowledge_hub.app.entity import DocumentMetaDataEntity, ChunkMetaDataEntity
from knowledge_hub.app.enums import FileType
from knowledge_hub.app.parser import DocumentParser
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
            parser: DocumentParser,
            chunker: Chunker,
            embedding_provider: EmbeddingProvider,
            vector_store: VectorStore,
            meta_data_service: DocumentMetaDataService,
    ):
        self.parser = parser
        self.chunker = chunker
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.meta_data_service = meta_data_service

    def ingest(self, file_path: str,file_type:FileType):
        doc_meta = None
        try:
            app_logger.info('=== IngestionService Pipeline Started ===')

            doc_hash=HashUtil.generate_file_hash(file_path)
            doc_meta=self.meta_data_service.get_doc_by_hash(doc_hash)
            if doc_meta is not None:
                app_logger.info(f'file is {doc_meta} already ingested,going to update')
                # Delete old chunks metadata first
                self.meta_data_service.delete_chunks_for_doc(doc_meta.document_id)
                doc_meta.status = "PROCESSING"
                self.meta_data_service.update_doc(doc_meta)
            else:
                app_logger.info(f'New file is detected {file_path}  for ingesting')
                doc_meta=DocumentMetaDataEntity(
                    file_name=file_path.split("/")[-1] if "/" in file_path else file_path.split("\\")[-1],
                    file_hash=doc_hash,
                    file_type=file_type.value,
                    status="PROCESSING"
                )
                self.meta_data_service.create_doc(doc_meta)
                app_logger.info('=== Document metadat stored in DB ===')



            documents = self.parser.parse(file_path,doc_meta)
            self.meta_data_service.update_doc(doc_meta)
            app_logger.info('=== Parsing Completed ===')

            chunks=self.chunker.chunk(documents)
            app_logger.info('=== Chunking Completed ===')

            embedded_chunks=self.embedding_provider.embed(chunks)
            app_logger.info('=== Embedding Completed ===')

            self.vector_store.upsert(embedded_chunks)
            
            # Save chunks metadata to relational database
            import uuid
            chunk_entities = []
            for chunk in chunks:
                chunk_entities.append(ChunkMetaDataEntity(
                    chunk_id=uuid.UUID(chunk.metadata.chunk_id),
                    document_id=doc_meta.document_id,
                    page_number=chunk.metadata.page_number,
                    chunk_hash=HashUtil.generate_chunk_hash(chunk.content),
                    vector_id=chunk.metadata.chunk_id
                ))
            self.meta_data_service.save_chunks(chunk_entities)
            app_logger.info('=== Chunk metadata stored in DB ===')
            
            doc_meta.status = "SUCCESS"
            self.meta_data_service.update_doc(doc_meta)
            app_logger.info('=== IngestionService Pipeline Completed ===')

        except Exception as e:
            app_logger.warning("Exception occurred in pipeline process", exc_info=True)
            if doc_meta is not None:
                try:
                    doc_meta.status = "FAILED"
                    self.meta_data_service.update_doc(doc_meta)
                except Exception as db_err:
                    app_logger.error(f"Failed to update document status to FAILED: {db_err}", exc_info=True)
            raise e



