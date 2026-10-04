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


def load_dataset() -> dict:
    with DATASET_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def build_qrels(dataset: dict) -> Qrels:
    qrels = {}

    for query in dataset["queries"]:
        qrels[query["query_id"]] = {
            memory_id: 1
            for memory_id in query["relevant_memory_ids"]
        }

    return Qrels(qrels)


def build_run(
    dataset: dict,
    embedding_provider: EmbeddingProvider,
    store: QdrantVectorStore,
    limit: int = 10,
) -> Run:

    run = {}

    for query in dataset["queries"]:

        query_id = query["query_id"]
        query_text = query["text"]

        # --------------------------------------------------
        # Query → Dense Embedding
        # --------------------------------------------------

        query_vector = embedding_provider.embed(
            query_text
        )

        # --------------------------------------------------
        # Dense Retrieval
        # --------------------------------------------------

        results = store.search(
            SearchRequest(
                mode=RetrievalMode.DENSE,
                dense_vector=query_vector,
                limit=limit,
            )
        )

        # --------------------------------------------------
        # JARVIS SearchResult → ranx Run
        # --------------------------------------------------

        run[query_id] = {
            result.memory_id: result.score
            for result in results
        }

        print(
            f"{query_id}: "
            f"{len(results)} results"
        )

    return Run(run)


def main() -> None:

    dataset = load_dataset()

    print(
        f"Loaded {len(dataset['corpus'])} memories."
    )

    print(
        f"Loaded {len(dataset['queries'])} queries."
    )

    # --------------------------------------------------
    # Ground Truth
    # --------------------------------------------------

    qrels = build_qrels(dataset)

    # --------------------------------------------------
    # JARVIS Components
    # --------------------------------------------------

    embedding_provider = EmbeddingProvider()

    store = QdrantVectorStore(
        collection_name="eval_memories",
    )

    # --------------------------------------------------
    # Retrieval
    # --------------------------------------------------

    run = build_run(
        dataset=dataset,
        embedding_provider=embedding_provider,
        store=store,
        limit=10,
    )

    # --------------------------------------------------
    # Evaluation
    # --------------------------------------------------

    results = evaluate(
        qrels,
        run,
      metrics=[
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
],
    )

    print("\nEvaluation Results:")
    print(results)


if __name__ == "__main__":
    main()