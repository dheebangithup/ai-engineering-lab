from pathlib import Path

import yaml

from jarvis.memory.embedding_engine import EmbeddingProvider
from jarvis.memory.vector_store import SparseVector
from jarvis.memory.vector_store.qdrant import QdrantVectorStore
from jarvis.memory.vector_store.sparse_encoder import (
    BM25SparseEncoder,
)

DATASET_PATH = (
    Path(__file__).parent
    / "datasets"
    / "golden_dataset.yaml"
)

COLLECTION_NAME = "eval_memories"


def load_dataset() -> dict:
    with DATASET_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return yaml.safe_load(file)


def main() -> None:
    dataset = load_dataset()

    corpus = dataset["corpus"]

    print(
        f"Loaded {len(corpus)} memories."
    )

    embedding_provider = EmbeddingProvider()

    store = QdrantVectorStore(
        collection_name=COLLECTION_NAME,
    )

    # Clear the existing evaluation collection
    # before feeding the golden dataset.
    store.delete_collection(COLLECTION_NAME)
    store.ensure_collection_exists()
    sparse_encoder = BM25SparseEncoder()
    for memory in corpus:
        memory_id = memory["memory_id"]

        text = (
            f"{memory['title']}\n"
            f"{memory['content']}"
        )

        # Dense embedding
        dense_vector = embedding_provider.embed(
            text
        )
        

        # Sparse embedding will be implemented later.
        sparse_vector = sparse_encoder.encode(text)

        # Metadata stored alongside vectors.
        payload = {
            "memory_type": memory["memory_type"],
            "title": memory["title"],
            "content": memory["content"],
            "tags": memory.get("tags", []),
        }

        store.add(
            memory_id=memory_id,
            dense_vector=dense_vector,
            sparse_vector=sparse_vector,
            payload=payload,
        )

        print(
            f"Indexed: {memory_id}"
        )

    print()
    print(
        f"Indexed {len(corpus)} memories "
        f"into '{COLLECTION_NAME}'."
    )


if __name__ == "__main__":
    main()