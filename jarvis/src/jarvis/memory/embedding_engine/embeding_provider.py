from pathlib import Path
from typing import Sequence

from llama_cpp import Llama

from .config import EmbeddingConfig
from .exceptions import ModelLoadError
from .model_manager import ModelManager


class EmbeddingProvider:

    def __init__(
        self,
        config: EmbeddingConfig | None = None,
    ):
        self.config = config or EmbeddingConfig()

        self.model_manager = ModelManager(
            self.config
        )

        self._model: Llama | None = None

    def _load_model(self) -> Llama:

        if self._model is not None:
            return self._model

        model_path = self.model_manager.ensure_model()

        print(f"Loading embedding model: {model_path}")

        try:
            self._model = Llama(
                model_path=str(model_path),

                embedding=True,

                n_ctx=self.config.context_size,

                pooling_type=self.config.pooling_type,

                verbose=self.config.verbose,
            )

        except Exception as exc:
            raise ModelLoadError(
                f"Failed to load embedding model: {exc}"
            ) from exc

        return self._model

    def embed(self, text: str) -> list[float]:
        """
        Generate an embedding for a single text.
        """

        if not text or not text.strip():
            raise ValueError(
                "Text cannot be empty."
            )

        model = self._load_model()

        result = model.create_embedding(text)

        embedding = result["data"][0]["embedding"]

        return embedding

    def embed_batch(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.
        """

        if not texts:
            return []

        if any(
            not text or not text.strip()
            for text in texts
        ):
            raise ValueError(
                "Batch contains empty text."
            )

        model = self._load_model()

        result = model.create_embedding(
            list(texts)
        )

        return [
            item["embedding"]
            for item in result["data"]
        ]

    @property
    def dimension(self) -> int:
        return self.config.embedding_dimension