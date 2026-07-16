from dataclasses import dataclass

from knowledge_hub.app.model.document_metadata import DocumentMetadata


@dataclass
class Document:
    content: str
    metadata: DocumentMetadata