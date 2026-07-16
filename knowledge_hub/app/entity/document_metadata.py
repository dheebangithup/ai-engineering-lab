from sqlalchemy import Column, String, Integer, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import  relationship
import uuid
from knowledge_hub.app.config.database import Base
from sqlalchemy.sql import func

class DocumentMetaDataEntity(Base):
    __tablename__ = "docs_metadata"

    document_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name = Column(String, nullable=False)
    file_hash = Column(String, nullable=False, unique=True)
    file_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    total_pages = Column(Integer)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    chunks = relationship("ChunkMetaDataEntity", back_populates="file", cascade="all, delete-orphan")

