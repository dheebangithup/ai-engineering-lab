from sqlalchemy.orm import Session

from knowledge_hub.app.entity.chunk_metadata import ChunkMetaDataEntity
from knowledge_hub.app.config import app_logger


class ChunkMetaDataRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_all(self, chunks: list[ChunkMetaDataEntity]):
        self.db.add_all(chunks)
        self.db.commit()
        return chunks

    def update(self, chunk: ChunkMetaDataEntity):
        try:
            app_logger.info(f"ChunkMetaDataRepository: Attempting to update chunk metadata with ID: {chunk.chunk_id}")
            if chunk.chunk_id is None:
                app_logger.error("ChunkMetaDataRepository: Validation failed - chunk_id is None.")
                raise ValueError("chunk_id must be provided for update.")
            
            merged_chunk = self.db.merge(chunk)
            self.db.commit()
            app_logger.info(f"ChunkMetaDataRepository: Successfully updated chunk metadata with ID: {chunk.chunk_id}")
            return merged_chunk
        except Exception as e:
            self.db.rollback()
            app_logger.error(f"ChunkMetaDataRepository: Failed to update chunk metadata with ID: {chunk.chunk_id if chunk else 'None'}. Error: {str(e)}", exc_info=True)
            raise e

    def update_all(self, chunks: list[ChunkMetaDataEntity]):
        try:
            chunk_ids = [str(c.chunk_id) for c in chunks]
            app_logger.info(f"ChunkMetaDataRepository: Attempting to bulk update {len(chunks)} chunk metadata records. IDs: {chunk_ids}")
            
            for index, chunk in enumerate(chunks):
                if chunk.chunk_id is None:
                    app_logger.error(f"ChunkMetaDataRepository: Validation failed - chunk at index {index} has chunk_id as None.")
                    raise ValueError(f"chunk_id must be provided for chunk at index {index}.")
                self.db.merge(chunk)
                app_logger.info(f" chunk {index} {chunk.chunk_id} updated")
                
            self.db.commit()
            app_logger.info(f"ChunkMetaDataRepository: Successfully bulk updated {len(chunks)} chunk metadata records.")
            return chunks
        except Exception as e:
            self.db.rollback()
            app_logger.error(f"ChunkMetaDataRepository: Failed to bulk update chunk metadata records. Error: {str(e)}", exc_info=True)
            raise e


    def find_by_document(self, document_id: str):
        return self.db.query(ChunkMetaDataEntity).filter(ChunkMetaDataEntity.document_id == document_id).all()

    def find_by_page(self, document_id: str, page_number: int):
        return  self.db.query(ChunkMetaDataEntity) .filter(ChunkMetaDataEntity.document_id == document_id, ChunkMetaDataEntity.page_number == page_number) .all()


    def delete_by_page(self, document_id: str, page_number: int):
        chunk = self.find_by_page(document_id, page_number)
        if chunk:
            self.db.delete(chunk)
            self.db.commit()
        return chunk

    def delete_by_document(self, document_id: str):
        chunks = self.find_by_document(document_id)
        for chunk in chunks:
            self.db.delete(chunk)
        self.db.commit()
        return chunks

    def delete_by_ids(self, chunk_ids: list):
        try:
            if not chunk_ids:
                app_logger.info("ChunkMetaDataRepository: No chunk IDs provided for deletion.")
                return
            app_logger.info(f"ChunkMetaDataRepository: Deleting {len(chunk_ids)} chunk metadata records by ID.")
            self.db.query(ChunkMetaDataEntity).filter(ChunkMetaDataEntity.chunk_id.in_(chunk_ids)).delete(synchronize_session=False)
            self.db.commit()
            app_logger.info("ChunkMetaDataRepository: Successfully deleted chunk metadata records in bulk.")
        except Exception as e:
            self.db.rollback()
            app_logger.error(f"ChunkMetaDataRepository: Failed to bulk delete chunk metadata records. Error: {str(e)}", exc_info=True)
            raise e