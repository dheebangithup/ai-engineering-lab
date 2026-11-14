import asyncio
import logging
from typing import List, Optional
from openai import AsyncOpenAI
from strata.config import settings

logger = logging.getLogger("strata.embedder")


class OllamaEmbedder:
    _instance: Optional["OllamaEmbedder"] = None

    def __init__(self) -> None:
        self.model_name = settings.embedding_model_name
        self._client: Optional[AsyncOpenAI] = None
        self._client_loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def client(self) -> AsyncOpenAI:
        try:
            curr_loop = asyncio.get_running_loop()
        except RuntimeError:
            curr_loop = None

        if self._client is None or self._client_loop != curr_loop:
            self._client = AsyncOpenAI(
                base_url=settings.embedding_base_url,
                api_key=settings.embedding_api_key,
            )
            self._client_loop = curr_loop
        return self._client

    @classmethod
    def get_instance(cls) -> "OllamaEmbedder":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def embed_one(self, text: str) -> List[float]:
        """Generates a dense vector embedding asynchronously using Ollama or OpenAI-compatible endpoint."""
        if not text:
            text = " "
        response = await self.client.embeddings.create(
            input=[text],
            model=self.model_name,
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates batch embeddings asynchronously."""
        if not texts:
            return []
        cleaned = [t if t else " " for t in texts]
        response = await self.client.embeddings.create(
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

