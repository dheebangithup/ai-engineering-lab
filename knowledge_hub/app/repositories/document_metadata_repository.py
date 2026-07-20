import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from knowledge_hub.app.entity.document_metadata import DocumentMetaDataEntity

logger = logging.getLogger("app")

class DocumentMetaDataRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, file: DocumentMetaDataEntity) -> DocumentMetaDataEntity:
        try:
            logger.info(f"DocumentMetaDataRepository: Saving document entity with file_name='{file.file_name}', hash='{file.file_hash}'")
            self.db.add(file)
            self.db.commit()
            self.db.refresh(file)
            logger.info(f"DocumentMetaDataRepository: Successfully saved document entity document_id='{file.document_id}'")
            return file
        except Exception as e:
            self.db.rollback()
            logger.error(f"DocumentMetaDataRepository: Failed to save document entity with file_name='{file.file_name}': {str(e)}", exc_info=True)
            raise e

    def update(self, file: DocumentMetaDataEntity) -> DocumentMetaDataEntity:
        try:
            logger.info(f"DocumentMetaDataRepository: Updating document entity document_id='{file.document_id}'")
            merged_file = self.db.merge(file)
            self.db.commit()
            logger.info(f"DocumentMetaDataRepository: Successfully updated document_id='{file.document_id}'")
            return merged_file
        except Exception as e:
            self.db.rollback()
            logger.error(f"DocumentMetaDataRepository: Failed to update document_id='{file.document_id}': {str(e)}", exc_info=True)
            raise e

    def find_by_document_id(self, document_id: str) -> Optional[DocumentMetaDataEntity]:
        try:
            logger.debug(f"DocumentMetaDataRepository: Searching for document_id='{document_id}'")
            return self.db.query(DocumentMetaDataEntity).filter(DocumentMetaDataEntity.document_id == document_id).first()
        except Exception as e:
            logger.error(f"DocumentMetaDataRepository: Error querying document_id='{document_id}': {str(e)}", exc_info=True)
            raise e

    def find_by_hash(self, file_hash: str) -> Optional[DocumentMetaDataEntity]:
        try:
            logger.debug(f"DocumentMetaDataRepository: Searching for document with hash='{file_hash}'")
            return self.db.query(DocumentMetaDataEntity).filter(DocumentMetaDataEntity.file_hash == file_hash).first()
        except Exception as e:
            logger.error(f"DocumentMetaDataRepository: Error querying file_hash='{file_hash}': {str(e)}", exc_info=True)
            raise e

    def find_all(self) -> List[DocumentMetaDataEntity]:
        try:
            logger.info("DocumentMetaDataRepository: Retrieving all document metadata entities ordered by created_at desc")
            documents = self.db.query(DocumentMetaDataEntity).order_by(DocumentMetaDataEntity.created_at.desc()).all()
            logger.info(f"DocumentMetaDataRepository: Successfully retrieved {len(documents)} document entities")
            return documents
        except Exception as e:
            logger.error(f"DocumentMetaDataRepository: Failed to retrieve document entities: {str(e)}", exc_info=True)
            raise e

    def delete(self, document_id: str) -> Optional[DocumentMetaDataEntity]:
        try:
            logger.info(f"DocumentMetaDataRepository: Request received to delete document_id='{document_id}'")
            file = self.find_by_document_id(document_id)
            if file:
                self.db.delete(file)
                self.db.commit()
                logger.info(f"DocumentMetaDataRepository: Successfully deleted document_id='{document_id}'")
            else:
                logger.warning(f"DocumentMetaDataRepository: Document not found for deletion document_id='{document_id}'")
            return file
        except Exception as e:
            self.db.rollback()
            logger.error(f"DocumentMetaDataRepository: Error deleting document_id='{document_id}': {str(e)}", exc_info=True)
            raise e



