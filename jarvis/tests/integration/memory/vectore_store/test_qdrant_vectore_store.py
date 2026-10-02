from jarvis.memory.vector_store import (
    RetrievalMode,
    SearchRequest,
    SparseVector,
)
from jarvis.memory.vector_store.qdrant import QdrantVectorStore


def main():

    store = QdrantVectorStore(
        collection_name="test_memories",
    )

    memory_id = "memory-payment-timeout-001"

    dense_vector = [0.1] * 1024

    sparse_vector = SparseVector(
        indices=[1, 5, 20],
        values=[0.8, 0.5, 0.3],
    )

    payload = {
        "memory_type": "lesson",
        "domain": "payments",
        "service": "payment-api",
        "environment": "production",
        "status": "active",
        "tags": [
            "timeout",
            "database",
        ],
    }

    # --------------------------------------------------
    # ADD
    # --------------------------------------------------

    store.add(
        memory_id=memory_id,
        dense_vector=dense_vector,
        sparse_vector=sparse_vector,
        payload=payload,
    )

    print("ADD: OK")

    # --------------------------------------------------
    # DENSE SEARCH
    # --------------------------------------------------

    results = store.search(
        SearchRequest(
            mode=RetrievalMode.DENSE,
            dense_vector=dense_vector,
            limit=5,
        )
    )

    print("DENSE:", results)

    # --------------------------------------------------
    # SPARSE SEARCH
    # --------------------------------------------------

    results = store.search(
        SearchRequest(
            mode=RetrievalMode.SPARSE,
            sparse_vector=sparse_vector,
            limit=5,
        )
    )

    print("SPARSE:", results)

    # --------------------------------------------------
    # HYBRID SEARCH
    # --------------------------------------------------

    results = store.search(
        SearchRequest(
            mode=RetrievalMode.HYBRID,
            dense_vector=dense_vector,
            sparse_vector=sparse_vector,
            limit=5,
        )
    )

    print("HYBRID:", results)

    # --------------------------------------------------
    # FILTERED SEARCH
    # --------------------------------------------------

    results = store.search(
        SearchRequest(
            mode=RetrievalMode.DENSE,
            dense_vector=dense_vector,
            filter={
                "memory_type": "lesson",
                "service": "payment-api",
                "environment": "production",
            },
            limit=5,
        )
    )

    print("FILTERED:", results)

    # --------------------------------------------------
    # UPDATE
    # --------------------------------------------------

    updated_payload = {
        "status": "active",
        "importance": 0.9,
    }

    store.update(
        memory_id=memory_id,
        payload=updated_payload,
    )

    print("UPDATE: OK")

    # --------------------------------------------------
    # DELETE
    # --------------------------------------------------

    store.delete(
        memory_id=memory_id,
    )

    print("DELETE: OK")


if __name__ == "__main__":
    main()