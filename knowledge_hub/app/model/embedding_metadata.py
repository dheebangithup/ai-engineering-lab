from dataclasses import dataclass


@dataclass
class EmbeddingMetadata:
    embedding_model: str
    vector_dimension: int
    embedding_time_ms: float