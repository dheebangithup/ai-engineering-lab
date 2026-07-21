import uuid
from typing import Optional
from knowledge_hub.app.config import app_logger
from knowledge_hub.app.database.vector_store import VectorStore
from knowledge_hub.app.embeddings.embedding_provider import EmbeddingProvider
from knowledge_hub.app.entity import DocumentMetaDataEntity, ChunkMetaDataEntity
from knowledge_hub.app.enums import FileType
from knowledge_hub.app.model import EmbeddedDocument, Document
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

    def ingest(self, file_path: str, file_type: FileType, doc_version: str, doc_id: str = None):
        doc_meta = None
        try:
            app_logger.info(f"IngestionService: Starting ingestion pipeline for file '{file_path}' (type={file_type.value}, doc_id={doc_id})")

            doc_hash = HashUtil.generate_file_hash(file_path)
            app_logger.info(f"IngestionService: Generated file hash '{doc_hash}'")

            valid_doc_uuid = None
            if doc_id and doc_id.strip() and doc_id != "string":
                try:
                    valid_doc_uuid = uuid.UUID(doc_id)
                    app_logger.info(f"IngestionService: Validated provided doc_id '{doc_id}' as a UUID.")
                except ValueError:
                    app_logger.warning(f"IngestionService: Provided doc_id '{doc_id}' is not a valid UUID format. Ignoring it.")

            # Try to fetch by doc_id first
            if valid_doc_uuid:
                app_logger.info(f"IngestionService: Querying DB for document_id '{valid_doc_uuid}'")
                doc_meta = self.meta_data_service.get_doc(str(valid_doc_uuid))
                if doc_meta:
                    app_logger.info(f"IngestionService: Found document with document_id '{valid_doc_uuid}' in DB.")

            # If not found by doc_id, fall back to hash-based lookup
            if not doc_meta:
                app_logger.info(f"IngestionService: Querying DB for document by file hash '{doc_hash}'")
                doc_meta = self.meta_data_service.get_doc_by_hash(doc_hash)
                if doc_meta:
                    app_logger.info(f"IngestionService: Found document with matching hash '{doc_hash}' in DB (document_id={doc_meta.document_id}).")

            is_update_flow = doc_meta is not None
            config_changed = False
            if is_update_flow:
                old_config = doc_meta.additional_data or {}
                config_changed = self.processor.compare_config(old_config)

                if config_changed:
                    app_logger.info(f"IngestionService: Configuration changed for document_id={doc_meta.document_id}. Triggering full reset (deleting existing chunks/vectors).")
                    # 1. Delete from DB
                    self.meta_data_service.delete_chunks_for_doc(doc_meta.document_id)
                    # 2. Delete from Qdrant
                    self.vector_store.delete_by_document(doc_meta.document_id)
                    app_logger.info("IngestionService: Finished clearing old chunks/vectors from relational DB and vector store.")

                    doc_meta.additional_data = self.processor.get_config()
                else:
                    app_logger.info(f"IngestionService: Configuration is identical for document_id={doc_meta.document_id}. Running partial update flow.")
                    # In case additional_data wasn't populated previously, we populate it
                    doc_meta.additional_data = self.processor.get_config()

                doc_meta.doc_version = doc_version
                doc_meta.status = "PROCESSING"
                self.meta_data_service.update_doc(doc_meta)
            else:
                file_name = file_path.split("/")[-1] if "/" in file_path else file_path.split("\\")[-1]
                app_logger.info(f"IngestionService: Document not found in DB. Creating new metadata record for '{file_name}'.")
                
                entity_kwargs = {
                    "file_name": file_name,
                    "file_hash": doc_hash,
                    "file_type": file_type.value,
                    "status": "PROCESSING",
                    "doc_version": doc_version,
                    "additional_data": self.processor.get_config()
                }
                if valid_doc_uuid:
                    entity_kwargs["document_id"] = valid_doc_uuid
                    app_logger.info(f"IngestionService: Reusing validated doc_id '{valid_doc_uuid}' as primary key UUID.")
                
                doc_meta = DocumentMetaDataEntity(**entity_kwargs)
                self.meta_data_service.create_doc(doc_meta)
                app_logger.info(f"IngestionService: Document metadata created in DB with ID: {doc_meta.document_id}")

            app_logger.info(f"IngestionService: Invoking document processor '{self.processor.__class__.__name__}'")
            documents = self.processor.process(file_path, doc_meta)
            
            # Update total pages and other info in metadata DB
            self.meta_data_service.update_doc(doc_meta)
            app_logger.info(f"IngestionService: Document processing completed. Generated {len(documents)} chunks.")

            if is_update_flow and not config_changed:
                # Compare and filter documents before generating embeddings
                documents_to_embed = self.update_doc(doc_meta, documents)
            else:
                # For new documents or config changes, embed all chunks
                documents_to_embed = documents

            if documents_to_embed:
                app_logger.info(f"IngestionService: Commencing chunk embedding generation for {len(documents_to_embed)} chunks.")
                embedded_chunks = self.embedding_provider.embed(documents_to_embed)
                app_logger.info(f"IngestionService: Embedding phase completed. Embedded {len(embedded_chunks)} chunks.")
                
                app_logger.info("IngestionService: Upserting embedded chunks into vector store.")
                self.vector_store.upsert(embedded_chunks)
                app_logger.info("IngestionService: Vector store upsert completed successfully.")
            else:
                app_logger.info("IngestionService: No chunks require embedding or vector store upsert (identical content).")
            
            if is_update_flow:
                app_logger.info(f"IngestionService: Bulk-updating doc_version payload in Qdrant for document_id={doc_meta.document_id} to '{doc_version}'.")
                self.vector_store.update_payload_by_document(str(doc_meta.document_id), {"doc_version": doc_version})
                app_logger.info("IngestionService: Finished bulk-updating Qdrant payload metadata.")

            # Save chunks metadata to relational database
            app_logger.info("IngestionService: Saving chunk metadata entities to relational database.")

            # To keep PostgreSQL metadata in sync (correct page indices, chunk indices, and new version),
            # we do NOT filter the 'documents' list. Instead, we update the doc_version on all chunk metadata
            # so that they are all written/merged in the database, preserving the full document's updated structure.
            chunk_entities = []
            for chunk in documents:
                chunk_entities.append(ChunkMetaDataEntity(
                    chunk_id=chunk.metadata.chunk_id,
                    document_id=doc_meta.document_id,
                    page_number=chunk.metadata.page_number if chunk.metadata.page_number is not None else 1,
                    chunk_hash=chunk.metadata.chunk_hash,
                    vector_id=chunk.metadata.chunk_id,
                    chunk_index=chunk.metadata.chunk_index,
                    doc_version=chunk.metadata.doc_version,
                    additional_data=chunk.metadata.to_dict()

                ))
            self.meta_data_service.update_chunks(chunk_entities)
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




    def update_doc(self, doc_meta: DocumentMetaDataEntity, chunks: list[Document]) -> list[Document]:
        #       Incremental indexing approch  we used
        try:
            # Log the start of the page-level invalidation and update process
            app_logger.info("IngestionService: Starting update_doc process for identical configuration flow.")
            # Fetch all existing chunk metadata records for this document from the database
            old_metadata = self.meta_data_service.get_chunks_for_doc(doc_meta.document_id)

            # Log the quantity of old versus newly parsed chunks to compare
            app_logger.info(f"IngestionService: update_doc comparing {len(old_metadata)} old existing chunks with {len(chunks)} new parsed chunks.")

            # Group the existing old chunks by their page number
            old_by_page = {}
            # Iterate through all database-fetched chunk metadata
            for chunk in old_metadata:
                # Default the page number to 1 if it is missing or invalid
                page_num = chunk.page_number if chunk.page_number else 1
                # Append the chunk to the list of chunks corresponding to this page number
                old_by_page.setdefault(page_num, []).append(chunk)

            # Sort the old chunks on each page by their index to guarantee proper sequence order
            for p_num in old_by_page:
                # Sort in place based on chunk_index
                old_by_page[p_num].sort(key=lambda x: x.chunk_index if x.chunk_index is not None else 0)

            # Group the newly parsed chunks by their page number
            new_by_page = {}
            # Iterate through all parsed chunks
            for ec in chunks:
                # Default the page number to 1 if it is missing or invalid
                page_num = ec.metadata.page_number if ec.metadata.page_number else 1
                # Append the chunk to the list of chunks corresponding to this page number
                new_by_page.setdefault(page_num, []).append(ec)

            # Sort the new chunks on each page by their index to guarantee proper sequence order
            for p_num in new_by_page:
                # Sort in place based on chunk_index
                new_by_page[p_num].sort(key=lambda x: x.metadata.chunk_index if x.metadata.chunk_index is not None else 0)

            # Set to collect page numbers that have been edited
            edited_pages = set()
            # Combine all page numbers from both old and new chunk sets
            all_pages = set(old_by_page.keys()).union(new_by_page.keys())
            # Iterate through each page number to check for changes
            # Refer to docs/page_invalidation_flow.md for details on page invalidation cases
            for p_num in all_pages:
                # CASE 1: Page Addition / Deletion (see docs/page_invalidation_flow.md)
                # If the page number is entirely missing from either the old or new document structure
                if p_num not in old_by_page or p_num not in new_by_page:
                    # Mark the page as edited
                    edited_pages.add(p_num)
                # CASE 2: Content Modifications & Boundary Shifts (see docs/page_invalidation_flow.md)
                # If the page exists in both versions, compare the chunk hashes
                else:
                    # Collect all hashes for old chunks on this page
                    old_hashes = [c.chunk_hash for c in old_by_page[p_num]]
                    # Collect all hashes for new chunks on this page
                    new_hashes = [c.metadata.chunk_hash for c in new_by_page[p_num]]
                    # Check if the list of hashes differs in order, length, or content
                    if old_hashes != new_hashes:
                        # Mark the page as edited due to content mismatch
                        edited_pages.add(p_num)

            # Default lowest edited page number to None
            min_edited_page = None
            # If any edited pages were found, calculate the lowest edited page number
            if edited_pages:
                # Find the minimum page number in the edited set
                min_edited_page = min(edited_pages)
                # Log the identified edited pages and the lowest edited page number
                app_logger.info(f"IngestionService: Edited pages detected: {edited_pages}. Lowest edited page: {min_edited_page}")
            # If no changes were found across any pages
            else:
                # Log that the document remains unchanged
                app_logger.info("IngestionService: No edited pages detected. Document is identical.")

            # If a lowest edited page was successfully determined
            if min_edited_page is not None:
                # Filter old chunks to identify those belonging to the lowest edited page or any subsequent page
                chunks_to_delete = [
                    x for x in old_metadata
                    if (x.page_number if x.page_number else 1) >= min_edited_page
                ]
                # Collect the chunk IDs of these obsolete/invalidated chunks
                orphaned_chunk_ids = [x.chunk_id for x in chunks_to_delete]

                # If there are obsolete chunks to delete
                if orphaned_chunk_ids:
                    # Log the list of chunk IDs that are being deleted
                    app_logger.info(f"IngestionService: Invalidation triggered. Deleting {len(orphaned_chunk_ids)} chunks from page {min_edited_page} onwards. IDs: {orphaned_chunk_ids}")
                    # Delete the records of these invalidated chunks from the PostgreSQL DB
                    self.meta_data_service.delete_chunks_by_ids(orphaned_chunk_ids)
                    # Delete the corresponding vector points from Qdrant
                    self.vector_store.delete([str(cid) for cid in orphaned_chunk_ids])
                    # Log that the clean invalidation step is complete
                    app_logger.info("IngestionService: Successfully deleted invalidated page chunks from relational DB and vector store.")
                # If no chunks were found on those pages to delete
                else:
                    # Log that no obsolete chunks were found for deletion
                    app_logger.info("IngestionService: No existing chunks found to delete on or after the lowest edited page.")

                # Keep only newly parsed chunks that belong to the lowest edited page or any subsequent page
                filtered_chunks = [
                    x for x in chunks
                    if (x.metadata.page_number if x.metadata.page_number else 1) >= min_edited_page
                ]

                # Detailed breakdown logging for invalidation
                reused_count = len(old_metadata) - len(orphaned_chunk_ids)
                reused_range = f"pages 1-{min_edited_page-1}" if min_edited_page > 1 else "None"
                app_logger.info(
                    f"IngestionService: Invalidation breakdown -> "
                    f"Reused chunks ({reused_range}): {reused_count}, "
                    f"Deleted old chunks (pages {min_edited_page}+): {len(orphaned_chunk_ids)}, "
                    f"New chunks to embed/upsert (pages {min_edited_page}+): {len(filtered_chunks)}, "
                    f"Net chunk count change: {len(chunks) - len(old_metadata):+d}."
                )
            # If no pages were edited (the entire document is unchanged)
            else:
                filtered_chunks = []

            # Log the total count of chunks that will be embedded and upserted to Qdrant
            app_logger.info(f"IngestionService: update_doc completed. {len(filtered_chunks)} chunks remain for vector store upsert.")
            # Return the filtered chunks list
            return filtered_chunks
        except Exception as e:
            app_logger.error("IngestionService: Error occurred in update_doc", exc_info=True)
            raise e