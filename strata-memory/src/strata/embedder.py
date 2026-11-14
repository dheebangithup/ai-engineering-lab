import logging
from typing import List, Optional
from openai import OpenAI
from strata.config import settings

logger = logging.getLogger("strata.embedder")


class OllamaEmbedder:
    _instance: Optional["OllamaEmbedder"] = None

    def __init__(self) -> None:
        self.model_name = settings.embedding_model_name
        self.client = OpenAI(
            base_url=settings.embedding_base_url,
            api_key=settings.embedding_api_key,
        )

    @classmethod
    def get_instance(cls) -> "OllamaEmbedder":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def embed_one(self, text: str) -> List[float]:
        """Generates a dense vector embedding using Ollama."""
        if not text:
            text = " "
        response = self.client.embeddings.create(
            input=[text],
            model=self.model_name,
        )
        return response.data[0].embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates batch embeddings using Ollama."""
        if not texts:
            return []
        cleaned = [t if t else " " for t in texts]
        response = self.client.embeddings.create(
            input=cleaned,
            model=self.model_name,
        )
        return [item.embedding for item in response.data]

    @staticmethod
    def to_pgvector_str(vec: List[float]) -> str:
        """Formats a float list into pgvector literal '[0.1,0.2,...]' for asyncpg."""
        return "[" + ",".join(f"{x:.7f}" for x in vec) + "]"


# Backward compatibility alias
LocalEmbedder = OllamaEmbedder
