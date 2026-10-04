from pathlib import Path

import pytest

from jarvis.memory.embedding_engine import EmbeddingProvider
from jarvis.memory.file_store import FileMemoryStore
from jarvis.memory.memory_manager import MemoryManager
from jarvis.memory.models import Memory, MemoryType
from jarvis.memory.vector_store.qdrant import QdrantVectorStore
from jarvis.memory.vector_store.enums import RetrievalMode
from jarvis.memory.vector_store.models import SearchRequest
from jarvis.memory.vector_store.sparse_encoder import (
    BM25SparseEncoder,
)
from jarvis.workspace import Workspace


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------


def create_runbook(
    memory_id: str = "mem_runbook_integration_001",
) -> Memory:
    return Memory(
        memory_id=memory_id,
        schema_version=1,
        memory_type=MemoryType.RUNBOOK,
        title="Payment API Timeout",
        domain="payments",
        category="incident",
        tags=[
            "payment",
            "timeout",
            "payment-api",
        ],
        content=(
            "Diagnose and resolve payment API timeout issues. "
            "Check payment API logs, database latency, and "
            "connection pool utilization. "
            "Verify successful payment requests after remediation."
        ),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def memory_manager(tmp_path: Path):
    # -----------------------------------------------------------------------
    # Canonical file store
    # -----------------------------------------------------------------------

    file_store = FileMemoryStore(
        tmp_path / "memories"
    )

    # -----------------------------------------------------------------------
    # Real embedding provider
    # -----------------------------------------------------------------------

    embedding_provider = EmbeddingProvider()

    # -----------------------------------------------------------------------
    # Real sparse encoder
    # -----------------------------------------------------------------------

    sparse_encoder = BM25SparseEncoder()

    # -----------------------------------------------------------------------
    # Test workspace
    #
    # Workspace is frozen, so do NOT mutate qdrant_dir after construction.
    # -----------------------------------------------------------------------

    workspace = Workspace(
        root=tmp_path / "jarvis",
    )

    # -----------------------------------------------------------------------
    # Real Qdrant store
    # -----------------------------------------------------------------------

    vector_store = QdrantVectorStore(
        workspace=workspace,
    )

    # -----------------------------------------------------------------------
    # Memory manager
    # -----------------------------------------------------------------------

    manager = MemoryManager(
        store=file_store,
        embedding_provider=embedding_provider,
        sparse_encoder=sparse_encoder,
        vector_store=vector_store,
    )

    return (
        manager,
        file_store,
        embedding_provider,
        sparse_encoder,
        vector_store,
    )


# ---------------------------------------------------------------------------
# ADD
# ---------------------------------------------------------------------------


def test_add_indexes_memory_in_qdrant(
    memory_manager,
):
    (
        manager,
        file_store,
        _,
        _,
        vector_store,
    ) = memory_manager

    memory = create_runbook()

    result = manager.add(memory)

    # -----------------------------------------------------------------------
    # Manager result
    # -----------------------------------------------------------------------

    assert result.memory_id == (
        "mem_runbook_integration_001"
    )

    # -----------------------------------------------------------------------
    # File store
    # -----------------------------------------------------------------------

    saved = file_store.get(
        "mem_runbook_integration_001"
    )

    assert saved is not None
    assert saved.memory_id == (
        "mem_runbook_integration_001"
    )
    assert saved.title == "Payment API Timeout"

    # -----------------------------------------------------------------------
    # Dense retrieval
    # -----------------------------------------------------------------------

    query = (
        "payment API timeout database "
        "connection pool"
    )

    query_embedding = (
        manager._embedding_provider.embed(query)
    )

    search_request = SearchRequest(
        dense_vector=query_embedding,
        mode=RetrievalMode.DENSE,
        limit=5,
    )

    results = vector_store.search(
        search_request
    )

    assert results

    assert results[0].memory_id == (
        "mem_runbook_integration_001"
    )


# ---------------------------------------------------------------------------
# ADD + METADATA FILTER
# ---------------------------------------------------------------------------


def test_add_indexes_memory_with_metadata_payload(
    memory_manager,
):
    (
        manager,
        _,
        _,
        _,
        vector_store,
    ) = memory_manager

    memory = create_runbook()

    manager.add(memory)

    query_embedding = (
        manager._embedding_provider.embed(
            "payment timeout"
        )
    )

    search_request = SearchRequest(
        dense_vector=query_embedding,
        mode=RetrievalMode.DENSE,
        limit=5,
        filter={
            "memory_type": "runbook",
        },
    )

    results = vector_store.search(
        search_request
    )

    assert results

    assert results[0].memory_id == (
        "mem_runbook_integration_001"
    )


# ---------------------------------------------------------------------------
# REINFORCE
# ---------------------------------------------------------------------------


def test_reinforce_updates_file_and_qdrant_payload(
    memory_manager,
):
    (
        manager,
        file_store,
        _,
        _,
        vector_store,
    ) = memory_manager

    memory = create_runbook()

    memory.importance.score = 0.5

    manager.add(memory)

    manager.reinforce(
        "mem_runbook_integration_001",
        importance_delta=0.2,
    )

    # -----------------------------------------------------------------------
    # File store
    # -----------------------------------------------------------------------

    saved = file_store.get(
        "mem_runbook_integration_001"
    )

    assert saved is not None

    assert saved.importance.score == pytest.approx(
        0.7
    )

    assert saved.usage.mention_count == 1

    # -----------------------------------------------------------------------
    # Qdrant
    # -----------------------------------------------------------------------

    query_embedding = (
        manager._embedding_provider.embed(
            "payment API timeout"
        )
    )

    search_request = SearchRequest(
        dense_vector=query_embedding,
        mode=RetrievalMode.DENSE,
        limit=5,
        filter={
            "memory_type": "runbook",
        },
    )

    results = vector_store.search(
        search_request
    )

    assert results

    assert results[0].memory_id == (
        "mem_runbook_integration_001"
    )


# ---------------------------------------------------------------------------
# DEPRECATE
# ---------------------------------------------------------------------------


def test_deprecate_removes_memory_from_qdrant(
    memory_manager,
):
    (
        manager,
        file_store,
        _,
        _,
        vector_store,
    ) = memory_manager

    memory = create_runbook()

    manager.add(memory)

    # Confirm it exists.
    query_embedding = (
        manager._embedding_provider.embed(
            "payment API timeout"
        )
    )

    search_request = SearchRequest(
        dense_vector=query_embedding,
        mode=RetrievalMode.DENSE,
        limit=5,
    )

    results = vector_store.search(
        search_request
    )

    assert results

    assert results[0].memory_id == (
        "mem_runbook_integration_001"
    )

    # -----------------------------------------------------------------------
    # Deprecate
    # -----------------------------------------------------------------------

    manager.deprecate(
        "mem_runbook_integration_001"
    )

    # -----------------------------------------------------------------------
    # File remains as source of truth
    # -----------------------------------------------------------------------

    saved = file_store.get(
        "mem_runbook_integration_001"
    )

    assert saved is not None
    assert saved.status.value == "deprecated"

    # -----------------------------------------------------------------------
    # Qdrant entry removed
    # -----------------------------------------------------------------------

    results = vector_store.search(
        search_request
    )

    matching_results = [
        result
        for result in results
        if result.memory_id
        == "mem_runbook_integration_001"
    ]

    assert matching_results == []


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------


def test_delete_removes_memory_from_file_and_qdrant(
    memory_manager,
):
    (
        manager,
        file_store,
        _,
        _,
        vector_store,
    ) = memory_manager

    memory = create_runbook()

    manager.add(memory)

    assert file_store.exists(
        "mem_runbook_integration_001"
    )

    # Confirm vector exists.
    query_embedding = (
        manager._embedding_provider.embed(
            "payment API timeout"
        )
    )

    search_request = SearchRequest(
        dense_vector=query_embedding,
        mode=RetrievalMode.DENSE,
        limit=5,
    )

    results = vector_store.search(
        search_request
    )

    assert results

    # -----------------------------------------------------------------------
    # Delete
    # -----------------------------------------------------------------------

    manager.delete(
        "mem_runbook_integration_001"
    )

    # -----------------------------------------------------------------------
    # File removed
    # -----------------------------------------------------------------------

    assert not file_store.exists(
        "mem_runbook_integration_001"
    )

    # -----------------------------------------------------------------------
    # Vector removed
    # -----------------------------------------------------------------------

    results = vector_store.search(
        search_request
    )

    matching_results = [
        result
        for result in results
        if result.memory_id
        == "mem_runbook_integration_001"
    ]

    assert matching_results == []


# ---------------------------------------------------------------------------
# SUPERSEDE
# ---------------------------------------------------------------------------


def test_supersede_replaces_qdrant_entry(
    memory_manager,
):
    (
        manager,
        file_store,
        _,
        _,
        vector_store,
    ) = memory_manager

    old_memory = create_runbook(
        "mem_runbook_old"
    )

    manager.add(old_memory)

    new_memory = create_runbook(
        "mem_runbook_new"
    )

    new_memory.title = (
        "Payment API Timeout - Updated"
    )

    new_memory.content = (
        "Updated payment timeout runbook. "
        "Check database connection pool and "
        "payment API latency before remediation."
    )

    result = manager.supersede(
        old_memory_id="mem_runbook_old",
        new_memory=new_memory,
    )

    # -----------------------------------------------------------------------
    # New memory
    # -----------------------------------------------------------------------

    assert result.memory_id == (
        "mem_runbook_new"
    )

    assert result.version == 2

    assert result.status.value == "active"

    assert "mem_runbook_old" in (
        result.relations.supersedes
    )

    # -----------------------------------------------------------------------
    # Old file
    # -----------------------------------------------------------------------

    old_saved = file_store.get(
        "mem_runbook_old"
    )

    assert old_saved is not None
    assert old_saved.status.value == "deprecated"

    # -----------------------------------------------------------------------
    # New file
    # -----------------------------------------------------------------------

    new_saved = file_store.get(
        "mem_runbook_new"
    )

    assert new_saved is not None
    assert new_saved.status.value == "active"

    # -----------------------------------------------------------------------
    # Search
    # -----------------------------------------------------------------------

    query_embedding = (
        manager._embedding_provider.embed(
            "updated payment API timeout"
        )
    )

    search_request = SearchRequest(
        dense_vector=query_embedding,
        mode=RetrievalMode.DENSE,
        limit=5,
    )

    results = vector_store.search(
        search_request
    )

    result_ids = [
        result.memory_id
        for result in results
    ]

    assert "mem_runbook_old" not in result_ids
    assert "mem_runbook_new" in result_ids


# ---------------------------------------------------------------------------
# MERGE
# ---------------------------------------------------------------------------


def test_merge_reindexes_target_and_removes_source(
    memory_manager,
):
    (
        manager,
        file_store,
        _,
        _,
        vector_store,
    ) = memory_manager

    target = create_runbook(
        "mem_runbook_target"
    )

    target.tags = [
        "payment",
        "timeout",
    ]

    source = create_runbook(
        "mem_runbook_source"
    )

    source.tags = [
        "database",
        "connection-pool",
    ]

    manager.add(target)
    manager.add(source)

    result = manager.merge(
        target_memory_id="mem_runbook_target",
        source_memory_id="mem_runbook_source",
    )

    # -----------------------------------------------------------------------
    # Target
    # -----------------------------------------------------------------------

    assert result.memory_id == (
        "mem_runbook_target"
    )

    assert result.version == 2

    assert "database" in result.tags
    assert "connection-pool" in result.tags

    assert "mem_runbook_source" in (
        result.relations.derived_from
    )

    # -----------------------------------------------------------------------
    # Source
    # -----------------------------------------------------------------------

    source_saved = file_store.get(
        "mem_runbook_source"
    )

    assert source_saved is not None
    assert source_saved.status.value == "deprecated"

    # -----------------------------------------------------------------------
    # Search
    # -----------------------------------------------------------------------

    query_embedding = (
        manager._embedding_provider.embed(
            "payment timeout database connection pool"
        )
    )

    search_request = SearchRequest(
        dense_vector=query_embedding,
        mode=RetrievalMode.DENSE,
        limit=10,
    )

    results = vector_store.search(
        search_request
    )

    result_ids = [
        result.memory_id
        for result in results
    ]

    assert "mem_runbook_source" not in result_ids
    assert "mem_runbook_target" in result_ids