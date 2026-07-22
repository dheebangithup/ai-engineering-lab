from sqlalchemy import Column, String, Float, TIMESTAMP, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from knowledge_hub.app.config.database import Base
from sqlalchemy.sql import func

class EvaluationRunEntity(Base):
    """
    Represents an evaluation run/session containing Ragas overall average scores.
    """
    __tablename__ = "evaluation_runs"

    run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_name = Column(String, nullable=True)
    provider = Column(String, nullable=False)
    eval_model = Column(String, nullable=False)
    
    # Aggregated Average Metrics
    avg_faithfulness = Column(Float, nullable=True)
    avg_answer_relevance = Column(Float, nullable=True)
    avg_context_recall = Column(Float, nullable=True)
    avg_context_precision = Column(Float, nullable=True)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    results = relationship("EvaluationResultEntity", back_populates="run", cascade="all, delete-orphan")


class EvaluationResultEntity(Base):
    """
    Represents the detailed evaluation metrics for a single question-answer query pair.
    """
    __tablename__ = "evaluation_results"

    result_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_runs.run_id", ondelete="CASCADE"), nullable=False)
    
    question = Column(String, nullable=False)
    contexts = Column(JSON, nullable=False)  # List of retrieved text chunks (strings)
    answer = Column(String, nullable=False)    # System-generated answer (string)
    ground_truth = Column(String, nullable=True) # Reference ground truth answer (string)
    
    # Metric Scores
    faithfulness = Column(Float, nullable=True)
    answer_relevance = Column(Float, nullable=True)
    context_recall = Column(Float, nullable=True)
    context_precision = Column(Float, nullable=True)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    run = relationship("EvaluationRunEntity", back_populates="results")
