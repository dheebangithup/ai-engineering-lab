from sqlalchemy import Column, String, Integer, TIMESTAMP, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
import uuid
from knowledge_hub.app.config.database import Base
from sqlalchemy.sql import func



class ChunkMetaDataEntity(Base):
    __tablename__ = "chunks_metadata"

    chunk_id = Column(UUID(as_uuid=True), primary_key=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("docs_metadata.document_id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    chunk_hash = Column(String, nullable=False)
    """
   System Flexibility & Portability: If we decide to change the vector database in the future to one that does not support UUIDs as point IDs (e.g., a vector database that only accepts auto-incrementing 64-bit integers), we only have to change the values generated in the vector_id column. The relational table structure and primary/foreign keys (chunk_id -> document_id) will remain entirely untouched and unbroken.
    """
    vector_id = Column(String)  # Reference to the corresponding point ID in the external vector database (e.g., Qdrant)
    chunk_index = Column(Integer, nullable=False)
    doc_version = Column(String, nullable=False)

    additional_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="extra  metadata"
    )
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    file = relationship("DocumentMetaDataEntity", back_populates="chunks")
