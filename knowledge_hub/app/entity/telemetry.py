import uuid
from sqlalchemy import Column, String, Integer, Float, TIMESTAMP, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from knowledge_hub.app.config.database import Base

class TelemetryLogEntity(Base):
    """
    Represents a query/retrieval execution event.
    Stores query details, answers, parameters, granular latencies, token counts, cost,
    and retrieved chunk metadata.
    """
    __tablename__ = "telemetry_logs"

    request_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query = Column(String, nullable=False)
    response_answer = Column(String, nullable=True)
    retrieval_mode = Column(String, nullable=False)
    
    # Model details
    llm_provider = Column(String, nullable=True)
    llm_model = Column(String, nullable=True)
    
    # Token usage & Cost
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    
    # Latencies (in milliseconds)
    llm_latency_ms = Column(Float, default=0.0)
    embedding_latency_ms = Column(Float, default=0.0)
    total_latency_ms = Column(Float, default=0.0)
    
    # Retrieved chunks and scores (JSON array)
    retrieved_chunks = Column(JSON, nullable=True)
    
    status = Column(String, nullable=False, default="SUCCESS")  # SUCCESS, FAILED
    error_message = Column(String, nullable=True)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class IngestionLogEntity(Base):
    """
    Represents a document ingestion event.
    Stores durations of individual pipeline stages: parsing, chunking, embedding, indexing.
    """
    __tablename__ = "ingestion_logs"

    ingestion_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), nullable=True)
    file_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=True)
    chunk_count = Column(Integer, default=0)
    
    # Latencies (in milliseconds)
    parsing_time_ms = Column(Float, default=0.0)
    chunking_time_ms = Column(Float, default=0.0)
    embedding_time_ms = Column(Float, default=0.0)
    vector_indexing_time_ms = Column(Float, default=0.0)
    total_time_ms = Column(Float, default=0.0)
    
    status = Column(String, nullable=False, default="SUCCESS")  # SUCCESS, FAILED
    error_message = Column(String, nullable=True)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
