from sqlalchemy.orm import Session

from knowledge_hub.app.entity.document_metadata import DocumentMetaDataEntity


class DocumentMetaDataRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, file: DocumentMetaDataEntity):
        self.db.add(file)
        self.db.commit()
        self.db.refresh(file)
        return file

    def update(self, file: DocumentMetaDataEntity):
        self.db.merge(file)
        self.db.commit()
        return file

    def find_by_document_id(self, document_id: str):
        return self.db.query(DocumentMetaDataEntity).filter(DocumentMetaDataEntity.document_id == document_id).first()

    def find_by_hash(self, file_hash: str):
        return self.db.query(DocumentMetaDataEntity).filter(DocumentMetaDataEntity.file_hash == file_hash).first()

    def delete(self, document_id: str):
        file = self.find_by_document_id(document_id)
        if file:
            self.db.delete(file)
            self.db.commit()
        return file


