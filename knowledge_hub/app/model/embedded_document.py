from dataclasses import dataclass

from knowledge_hub.app.model import Document


@dataclass
class EmbeddedDocument:
    document: Document
    embedding: list[float]