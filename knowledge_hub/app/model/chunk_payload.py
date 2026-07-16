from dataclasses import dataclass, asdict


@dataclass
class ChunkPayload:
    document_id: str
    chunk_id: str
    page_number: int
    source: str
    file_name: str
    content: str

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "ChunkPayload":
        return ChunkPayload(**data)