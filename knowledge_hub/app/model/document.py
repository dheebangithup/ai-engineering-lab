from dataclasses import dataclass
from typing import Optional

from knowledge_hub.app.model.document_metadata import DocumentMetadata


@dataclass
class Document:
    content: str = ""
    metadata: Optional[DocumentMetadata] = None