from dataclasses import dataclass

from llama_cpp import llama_cpp


@dataclass(frozen=True)
class EmbeddingConfig:
    model_repo: str = "Qwen/Qwen3-Embedding-0.6B-GGUF"
    model_filename: str = "Qwen3-Embedding-0.6B-Q8_0.gguf"
    context_size: int = 2048
    pooling_type: int = llama_cpp.LLAMA_POOLING_TYPE_LAST
    embedding_dimension: int = 1024
    verbose: bool = False