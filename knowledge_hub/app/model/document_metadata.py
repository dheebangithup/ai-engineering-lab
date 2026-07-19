from dataclasses import dataclass, asdict, field
from typing import Optional
from uuid import UUID

from knowledge_hub.app.enums import FileType, ParserType


@dataclass
class DocumentMetadata:
    doc_id: str
    source: str
    file_name:str
    file_type: FileType
    parser: ParserType
    doc_version: str
    page_number: Optional[int] = None
    chunk_id: Optional[UUID] = None
    chunk_hash: Optional[str] = None
    chunk_index: Optional[int] = None
    has_image: bool = False
    has_table: bool = False
    table_as_html: list[str] = field(default_factory=list)
    images_as_base64: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)

        if self.chunk_id:
            data["chunk_id"] = str(self.chunk_id)

        if self.parser:
            data["parser"] = self.parser.value

        if self.file_type:
            data["file_type"] = self.file_type.value

        return data

    @classmethod
    def from_dict(cls, data: dict) -> "DocumentMetadata":
        return cls(
            doc_id=data.get("doc_id"),
            chunk_id=data.get("chunk_id"),
            source=data.get("source"),
            file_name=data.get("file_name"),
            file_type=FileType(data["file_type"]) if data.get("file_type") and isinstance(data["file_type"], str) else data.get("file_type"),
            page_number=data.get("page_number"),
            parser=ParserType(data["parser"]) if data.get("parser") else None,
            doc_version=data.get("doc_version"),
            has_image=data.get("has_image", False),
            has_table=data.get("has_table", False),
            table_as_html=data.get("table_as_html", []),
            images_as_base64=data.get("images_as_base64", []),
            chunk_hash=data.get("chunk_hash", None),
            chunk_index=data.get("chunk_index", None),
        )