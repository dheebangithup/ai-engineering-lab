from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EmbeddingConfig:
    model_repo: str = "Qwen/Qwen3-Embedding-0.6B-GGUF"
    model_filename: str = "Qwen3-Embedding-0.6B-Q8_0.gguf"

    model_dir: Path = Path("models")

    context_size: int = 2048
    pooling_type: int = 1

    embedding_dimension: int = 1024

    verbose: bool = False