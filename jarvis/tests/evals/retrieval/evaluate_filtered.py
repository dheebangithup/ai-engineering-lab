from pathlib import Path

import yaml
from ranx import Qrels, Run, evaluate

from jarvis.memory.embedding_engine import EmbeddingProvider
from jarvis.memory.vector_store import (
    
    RetrievalMode,
    SearchRequest,
)

from jarvis.memory.vector_store.qdrant import QdrantVectorStore

DATASET_PATH = (
    Path(__file__).parent
    / "datasets"
    / "golden_dataset.yaml"
)

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
    with DATASET_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return yaml.safe_load(file)


def build_qrels(
    dataset: dict,
    memory_type: str,
) -> Qrels:
    """
    Build Qrels for filtered queries.

    Only queries with:

        filter:
          memory_type: <memory_type>

    are included.
    """

    qrels = {}

    for query in dataset["queries"]:

        query_filter = query.get("filter")

        # Ignore normal/unfiltered queries.
        if not query_filter:
            continue

        # Only include queries for the requested
        # memory type.
        if query_filter.get("memory_type") != memory_type:
            continue

        relevant = {
            memory_id: 1
            for memory_id in query["relevant_memory_ids"]
        }

        qrels[query["query_id"]] = relevant

    return Qrels(qrels)


def build_run(
    dataset: dict,
    embedding_provider: EmbeddingProvider,
    store: QdrantVectorStore,
    memory_type: str,
    limit: int = 10,
) -> Run:
    """
    Run dense retrieval using a metadata filter.

    The VectorStore abstraction expects the filter
    as a dictionary, not a Qdrant Filter object.
    """

    results = {}

    # IMPORTANT:
    # SearchRequest.filter expects a dict because
    # QdrantVectorStore._build_filter() calls .items().
    metadata_filter = {
        "memory_type": memory_type,
    }

    for query in dataset["queries"]:

        query_filter = query.get("filter")

        # Ignore normal/unfiltered queries.
        if not query_filter:
            continue

        # Only evaluate queries for the requested
        # memory type.
        if query_filter.get("memory_type") != memory_type:
            continue

        query_id = query["query_id"]
        query_text = query["text"]

        print(
            f"Embedding query: {query_id}"
        )

        query_vector = embedding_provider.embed(
            query_text
        )

        search_request = SearchRequest(
            mode=RetrievalMode.DENSE,
            dense_vector=query_vector,
            limit=limit,
            filter=metadata_filter,
        )

        search_results = store.search(
            search_request
        )

        results[query_id] = {
            result.memory_id: result.score
            for result in search_results
        }

        print(
            f"{query_id}: "
            f"{len(search_results)} results "
            f"[memory_type={memory_type}]"
        )

    return Run(results)


def evaluate_filtered(
    dataset: dict,
    embedding_provider: EmbeddingProvider,
    store: QdrantVectorStore,
    memory_type: str,
) -> None:
    """
    Evaluate one metadata-filtered retrieval scenario.
    """

    print()
    print(
        f"Building Qrels "
        f"[memory_type={memory_type}]"
    )

    qrels = build_qrels(
        dataset,
        memory_type=memory_type,
    )

    print(
        f"Building Run "
        f"[memory_type={memory_type}]"
    )

    run = build_run(
        dataset=dataset,
        embedding_provider=embedding_provider,
        store=store,
        memory_type=memory_type,
        limit=10,
    )

    print()
    print(
        f"Running evaluation "
        f"[memory_type={memory_type}]"
    )

    evaluation = evaluate(
        qrels,
        run,
        metrics=METRICS,
    )

    print()
    print("=" * 60)
    print(
        f"Evaluation Results "
        f"[memory_type={memory_type}]"
    )
    print("=" * 60)

    for metric, value in evaluation.items():
        print(
            f"{metric}: {value}"
        )


def main() -> None:

    dataset = load_dataset()

    corpus = dataset["corpus"]
    queries = dataset["queries"]

    filtered_queries = [
        query
        for query in queries
        if query.get("filter")
    ]

    print(
        f"Loaded {len(corpus)} memories."
    )

    print(
        f"Loaded {len(queries)} total queries."
    )

    print(
        f"Loaded {len(filtered_queries)} "
        f"filtered queries."
    )

    print()

    embedding_provider = EmbeddingProvider()

    store = QdrantVectorStore(
        collection_name=COLLECTION_NAME,
    )

    # ============================================================
    # RUNBOOK FILTER
    # ============================================================

    print("=" * 60)
    print("RUNBOOK FILTER EVALUATION")
    print("=" * 60)

    evaluate_filtered(
        dataset=dataset,
        embedding_provider=embedding_provider,
        store=store,
        memory_type="runbook",
    )

    # ============================================================
    # LESSON FILTER
    # ============================================================

    print()
    print()
    print("=" * 60)
    print("LESSON FILTER EVALUATION")
    print("=" * 60)

    evaluate_filtered(
        dataset=dataset,
        embedding_provider=embedding_provider,
        store=store,
        memory_type="lesson",
    )


if __name__ == "__main__":
    main()