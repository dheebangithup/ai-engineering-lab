from langchain_core.documents import Document as LCDocument
from qdrant_client.http.models import PointStruct

from knowledge_hub.app.model import Document, DocumentMetadata, EmbeddedDocument
from knowledge_hub.app.model.chunk_payload import ChunkPayload
from knowledge_hub.app.utils.hash_util import HashUtil


class DocumentUtil:




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
            doc_version=meta.doc_version,
            chuk_index=meta.chunk_index

        )

    @staticmethod
    def to_point(document: EmbeddedDocument) -> PointStruct:
        metadata = document.document.metadata

        return PointStruct(
            id=metadata.chunk_id,
            vector=document.embedding,
            payload=DocumentUtil.get_chunk_payload(document.document).to_dict(),
        )

