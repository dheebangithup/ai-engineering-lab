from knowledge_hub.app.entity import DocumentMetaDataEntity,ChunkMetaDataEntity
from knowledge_hub.app.repositories import DocumentMetaDataRepository
from knowledge_hub.app.repositories.chunk_metadata_repository import ChunkMetaDataRepository


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

    def delete_doc_and_chunks(self, document_id: str):
        self.chunk_repo.delete_by_document(document_id)
        return self.doc_repo.delete(document_id)

    def get_chunks_for_doc(self, document_id: str)->list[ChunkMetaDataEntity]:
        return self.chunk_repo.find_by_document(document_id)

    def get_chunk_by_page(self, document_id: str, page_number: int)->list[ChunkMetaDataEntity]:
        return self.chunk_repo.find_by_page(document_id, page_number)

    def delete_chunk_by_page(self, document_id: str, page_number: int)->ChunkMetaDataEntity:
        return self.chunk_repo.delete_by_page(document_id, page_number)
