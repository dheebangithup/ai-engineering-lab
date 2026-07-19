import uuid
from dataclasses import dataclass, asdict


@dataclass
class ChunkPayload:
    document_id: str
    chunk_id: uuid.UUID
    page_number: int
    source: str
    file_name: str
    content: str
    doc_version:str
    chuk_index:int


    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "ChunkPayload":
        if "chunk_id" in data and isinstance(data["chunk_id"], str):
            data = data.copy()
            data["chunk_id"] = uuid.UUID(data["chunk_id"])
        return ChunkPayload(**data)
