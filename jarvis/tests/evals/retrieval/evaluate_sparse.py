from pathlib import Path

import yaml
from ranx import Qrels, Run, evaluate

from jarvis.memory.embedding_engine import EmbeddingProvider
from jarvis.memory.vector_store.qdrant.qdrant_vector_store import QdrantVectorStore
from jarvis.memory.vector_store import RetrievalMode, SearchRequest
from jarvis.memory.vector_store.sparse_encoder import BM25SparseEncoder


DATASET_PATH = Path(__file__).parent / "datasets" / "golden_dataset.yaml"

COLLECTION_NAME = "eval_memories"

METRICS = [
    "precision@3",
    "precision@5",
    "precision@10",
    "recall@3",
    "recall@5",
    "recall@10",
    "mrr@3",
    "mrr@5",
    "mrr@10",
    "ndcg@3",
    "ndcg@5",
    "ndcg@10",
]


def load_dataset() -> dict:
    with DATASET_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def build_qrels(dataset: dict) -> Qrels:
    qrels = {}

    for query in dataset["queries"]:
        # Sparse baseline evaluation uses unfiltered queries.
        if query.get("filter"):
            continue

        qrels[query["query_id"]] = {
            memory_id: 1
            for memory_id in query["relevant_memory_ids"]
        }

    return Qrels(qrels)


def build_run(
    dataset: dict,
    sparse_encoder: BM25SparseEncoder,
    store: QdrantVectorStore,
    limit: int = 10,
) -> Run:
    results = {}

    for query in dataset["queries"]:
        # Sparse baseline evaluation uses unfiltered queries.
        if query.get("filter"):
            continue

        query_id = query["query_id"]
        query_text = query["text"]

        sparse_vector = sparse_encoder.encode(query_text)

        search_request = SearchRequest(
            mode=RetrievalMode.SPARSE,
            sparse_vector=sparse_vector,
            limit=limit,
        )

        search_results = store.search(search_request)

        results[query_id] = {
            result.memory_id: result.score
            for result in search_results
        }

    return Run(results)


def evaluate_sparse(
    dataset: dict,
    sparse_encoder: BM25SparseEncoder,
    store: QdrantVectorStore,
) -> None:
    qrels = build_qrels(dataset)

    run = build_run(
        dataset=dataset,
        sparse_encoder=sparse_encoder,
        store=store,
    )

    evaluation = evaluate(
        qrels,
        run,
        metrics=METRICS,
    )

    print("\n=== Sparse Retrieval Evaluation ===")

    for metric, score in evaluation.items():
        print(f"{metric}: {score}")


def main() -> None:
    dataset = load_dataset()

    embedding_provider = EmbeddingProvider()

    # Keep the same sparse encoder instance for
    # corpus/query vocabulary consistency.
    sparse_encoder = BM25SparseEncoder()

    store = QdrantVectorStore(
        collection_name=COLLECTION_NAME,
    )

    evaluate_sparse(
        dataset=dataset,
        sparse_encoder=sparse_encoder,
        store=store,
    )


if __name__ == "__main__":
    main()