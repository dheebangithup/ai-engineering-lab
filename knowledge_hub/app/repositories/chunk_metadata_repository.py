from sqlalchemy.orm import Session

from knowledge_hub.app.entity.chunk_metadata import ChunkMetaDataEntity


class ChunkMetaDataRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_all(self, chunks: list[ChunkMetaDataEntity]):
        self.db.add_all(chunks)
        self.db.commit()
        return chunks

    def update(self, chunk: ChunkMetaDataEntity):
        self.db.merge(chunk)
        self.db.commit()
        return chunk

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