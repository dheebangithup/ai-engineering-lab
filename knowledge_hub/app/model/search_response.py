from typing import Optional
from pydantic.dataclasses import dataclass

from knowledge_hub.app.model import Document
from knowledge_hub.app.model.chunk_payload import ChunkPayload


@dataclass
class SearchResult:
    document: ChunkPayload
    score: float


@dataclass
class SearchResponse:
    results: list[SearchResult]
    metadata: Optional[dict] = None