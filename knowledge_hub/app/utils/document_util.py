from langchain_core.documents import Document as LCDocument
from qdrant_client.http.models import PointStruct

from knowledge_hub.app.model import Document, DocumentMetadata, EmbeddedDocument
from knowledge_hub.app.model.chunk_payload import ChunkPayload
from knowledge_hub.app.utils.hash_util import HashUtil


class DocumentUtil:

    @staticmethod
    def to_lang_chain_document(docs: list[Document]) -> list[LCDocument]:
        return [LCDocument(page_content=doc.content, metadata=doc.metadata.to_dict()) for doc in docs]

    @staticmethod
    def to_document_from_lang_chain(docs: list[LCDocument], generate_chunk_id: bool = False) -> list[Document]:
        if generate_chunk_id:
            output_docs = []
            for i, doc in enumerate(docs, start=1):
                meta = DocumentMetadata.from_dict(doc.metadata)
                meta.chunk_id = HashUtil.generate_chunk_id(meta.doc_id, meta.page_number, i)
                output_docs.append(Document(
                    content=doc.page_content,
                    metadata=meta,
                ))
            return output_docs

        return [Document(
            content=doc.page_content,
            metadata=DocumentMetadata.from_dict(doc.metadata),
        ) for doc in docs]


    @staticmethod
    def get_chunk_payload(doc: Document) -> ChunkPayload:
        meta=doc.metadata
        return ChunkPayload(
           document_id=meta.doc_id,
            chunk_id=meta.chunk_id,
            page_number=meta.page_number,
            source=meta.source,
            file_name=meta.file_name,
            content=doc.content,

        )

    @staticmethod
    def to_point(document: EmbeddedDocument) -> PointStruct:
        metadata = document.document.metadata

        return PointStruct(
            id=metadata.chunk_id,
            vector=document.embedding,
            payload=DocumentUtil.get_chunk_payload(document.document).to_dict(),
        )

