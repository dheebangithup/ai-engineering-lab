import math
import re
from collections import Counter

from qdrant_client.models import SparseVector

from jarvis.memory.vector_store.sparse_encoder.sparse_encoder import (
    SparseEncoder,
)


class BM25SparseEncoder(SparseEncoder):

    def __init__(
        self,
        vocabulary: dict[str, int] | None = None,
    ) -> None:
        self._vocabulary = vocabulary or {}

    def encode(
        self,
        text: str,
    ) -> SparseVector:

        tokens = self._tokenize(text)

        if not tokens:
            return SparseVector(
                indices=[],
                values=[],
            )

        term_counts = Counter(tokens)

        indices: list[int] = []
        values: list[float] = []

        for token, frequency in term_counts.items():

            index = self._get_token_index(token)

            # Simple BM25-style term weight.
            weight = 1.0 + math.log(
                1.0 + frequency
            )

            indices.append(index)
            values.append(weight)

        return SparseVector(
            indices=indices,
            values=values,
        )

    def encode_batch(
        self,
        texts: list[str],
    ) -> list[SparseVector]:

        return [
            self.encode(text)
            for text in texts
        ]

    def _tokenize(
        self,
        text: str,
    ) -> list[str]:

        return re.findall(
            r"\b[a-zA-Z0-9_]+\b",
            text.lower(),
        )

    def _get_token_index(
        self,
        token: str,
    ) -> int:

        if token not in self._vocabulary:
            self._vocabulary[token] = (
                len(self._vocabulary) + 1
            )

        return self._vocabulary[token]