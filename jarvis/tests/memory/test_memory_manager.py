from pathlib import Path

import pytest

from jarvis.memory.file_store import FileMemoryStore
from jarvis.memory.memory_manager import MemoryManager
from jarvis.memory.models import (
    Memory,
    MemoryRelations,
    MemoryStatus,
    MemoryType,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeEmbeddingProvider:
    def __init__(self):
        self.calls: list[str] = []

    def embed(self, text: str):
        self.calls.append(text)
        return [0.1, 0.2, 0.3]


class FakeSparseEncoder:
    def __init__(self):
        self.calls: list[str] = []

    def encode(self, text: str):
        self.calls.append(text)

        return {
            "indices": [1, 2],
            "values": [1.0, 0.5],
        }


class FakeVectorStore:
    def __init__(self):
        self.items = {}

        self.add_calls = []
        self.update_calls = []
        self.delete_calls = []

    def add(
        self,
        memory_id,
        dense_vector,
        sparse_vector,
        payload,
    ):
        self.add_calls.append(
            {
                "memory_id": memory_id,
                "dense_vector": dense_vector,
                "sparse_vector": sparse_vector,
                "payload": payload,
            }
        )

        self.items[memory_id] = {
            "dense_vector": dense_vector,
            "sparse_vector": sparse_vector,
            "payload": payload,
        }

    def update(
        self,
        memory_id,
        dense_vector=None,
        sparse_vector=None,
        payload=None,
    ):
        self.update_calls.append(
            {
                "memory_id": memory_id,
                "dense_vector": dense_vector,
                "sparse_vector": sparse_vector,
                "payload": payload,
            }
        )

        if memory_id not in self.items:
            raise KeyError(memory_id)

        item = self.items[memory_id]

        if dense_vector is not None:
            item["dense_vector"] = dense_vector

        if sparse_vector is not None:
            item["sparse_vector"] = sparse_vector

        if payload is not None:
            item["payload"] = payload

    def delete(self, memory_id):
        self.delete_calls.append(memory_id)
        self.items.pop(memory_id, None)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def create_manager(tmp_path: Path):
    store = FileMemoryStore(tmp_path)

    embedding_provider = FakeEmbeddingProvider()
    sparse_encoder = FakeSparseEncoder()
    vector_store = FakeVectorStore()

    manager = MemoryManager(
        store=store,
        embedding_provider=embedding_provider,
        sparse_encoder=sparse_encoder,
        vector_store=vector_store,
    )

    return (
        manager,
        store,
        embedding_provider,
        sparse_encoder,
        vector_store,
    )


def create_memory(
    memory_id: str = "mem_001",
    title: str = "Payment API Timeout",
    memory_type: MemoryType = MemoryType.RUNBOOK,
    content: str = "Diagnose and resolve payment API timeout issues.",
    tags: list[str] | None = None,
) -> Memory:
    return Memory(
        memory_id=memory_id,
        schema_version=1,
        memory_type=memory_type,
        title=title,
        domain="payments",
        category="incident",
        tags=tags or ["payment", "timeout"],
        status=MemoryStatus.ACTIVE,
        content=content,
    )


# ---------------------------------------------------------------------------
# ADD
# ---------------------------------------------------------------------------


def test_add_saves_memory_and_indexes_it(tmp_path):
    (
        manager,
        store,
        embedding_provider,
        sparse_encoder,
        vector_store,
    ) = create_manager(tmp_path)

    memory = create_memory()

    result = manager.add(memory)

    # Returned object
    assert result is memory

    # Canonical file store
    saved = store.get("mem_001")

    assert saved is not None
    assert saved.memory_id == "mem_001"
    assert saved.title == "Payment API Timeout"
    assert saved.status == MemoryStatus.ACTIVE

    # Lifecycle timestamps
    assert saved.created_at is not None
    assert saved.updated_at is not None

    # Dense embedding was generated
    assert len(embedding_provider.calls) == 1
    assert "Payment API Timeout" in embedding_provider.calls[0]
    assert "payment" in embedding_provider.calls[0]
    assert "timeout" in embedding_provider.calls[0]

    # Sparse embedding was generated
    assert len(sparse_encoder.calls) == 1
    assert sparse_encoder.calls[0] == embedding_provider.calls[0]

    # Vector index
    assert len(vector_store.add_calls) == 1

    add_call = vector_store.add_calls[0]

    assert add_call["memory_id"] == "mem_001"
    assert add_call["dense_vector"] == [0.1, 0.2, 0.3]
    assert add_call["sparse_vector"] == {
        "indices": [1, 2],
        "values": [1.0, 0.5],
    }

    payload = add_call["payload"]

    assert payload["memory_id"] == "mem_001"
    assert payload["memory_type"] == "runbook"
    assert payload["title"] == "Payment API Timeout"
    assert payload["domain"] == "payments"
    assert payload["category"] == "incident"
    assert payload["tags"] == ["payment", "timeout"]
    assert payload["status"] == "active"
    assert payload["version"] == 1


def test_add_rejects_duplicate(tmp_path):
    manager, store, _, _, vector_store = create_manager(tmp_path)

    memory = create_memory()

    manager.add(memory)

    with pytest.raises(
        ValueError,
        match="Memory already exists: mem_001",
    ):
        manager.add(
            create_memory(
                memory_id="mem_001",
                title="Duplicate Memory",
            )
        )

    # Only one canonical memory/index entry exists.
    saved = store.get("mem_001")

    assert saved is not None
    assert saved.title == "Payment API Timeout"

    assert len(vector_store.add_calls) == 1


# ---------------------------------------------------------------------------
# GET
# ---------------------------------------------------------------------------


def test_get_returns_existing_memory(tmp_path):
    manager, store, _, _, _ = create_manager(tmp_path)

    memory = create_memory()

    store.save(memory)

    result = manager.get("mem_001")

    assert result is not None
    assert result.memory_id == "mem_001"
    assert result.title == "Payment API Timeout"


def test_get_returns_none_for_missing_memory(tmp_path):
    manager, _, _, _, _ = create_manager(tmp_path)

    result = manager.get("does_not_exist")

    assert result is None


# ---------------------------------------------------------------------------
# REINFORCE
# ---------------------------------------------------------------------------


def test_reinforce_updates_memory_and_vector_payload(tmp_path):
    (
        manager,
        store,
        _,
        _,
        vector_store,
    ) = create_manager(tmp_path)

    memory = create_memory()
    memory.importance.score = 0.5

    manager.add(memory)

    result = manager.reinforce(
        "mem_001",
        importance_delta=0.2,
    )

    assert result.importance.score == pytest.approx(0.7)
    assert result.usage.mention_count == 1
    assert result.updated_at is not None

    # File is updated
    saved = store.get("mem_001")

    assert saved is not None
    assert saved.importance.score == pytest.approx(0.7)
    assert saved.usage.mention_count == 1

    # Vector payload is updated without re-embedding.
    assert len(vector_store.update_calls) == 1

    update_call = vector_store.update_calls[0]

    assert update_call["memory_id"] == "mem_001"
    assert update_call["dense_vector"] is None
    assert update_call["sparse_vector"] is None

    payload = update_call["payload"]

    assert payload["memory_id"] == "mem_001"
    assert payload["status"] == "active"
    assert payload["version"] == 1


def test_reinforce_caps_importance_at_one(tmp_path):
    manager, store, _, _, _ = create_manager(tmp_path)

    memory = create_memory()
    memory.importance.score = 0.95

    manager.add(memory)

    result = manager.reinforce(
        "mem_001",
        importance_delta=0.5,
    )

    assert result.importance.score == 1.0

    saved = store.get("mem_001")

    assert saved is not None
    assert saved.importance.score == 1.0


def test_reinforce_missing_memory_fails(tmp_path):
    manager, _, _, _, _ = create_manager(tmp_path)

    with pytest.raises(
        ValueError,
        match="Memory not found: missing",
    ):
        manager.reinforce("missing")


# ---------------------------------------------------------------------------
# DEPRECATE
# ---------------------------------------------------------------------------


def test_deprecate_removes_memory_from_vector_index(tmp_path):
    (
        manager,
        store,
        _,
        _,
        vector_store,
    ) = create_manager(tmp_path)

    memory = create_memory()

    manager.add(memory)

    assert "mem_001" in vector_store.items

    result = manager.deprecate("mem_001")

    assert result.status == MemoryStatus.DEPRECATED

    # Canonical file remains.
    saved = store.get("mem_001")

    assert saved is not None
    assert saved.status == MemoryStatus.DEPRECATED

    # Vector entry is removed.
    assert "mem_001" not in vector_store.items

    assert vector_store.delete_calls == [
        "mem_001"
    ]


def test_deprecate_missing_memory_fails(tmp_path):
    manager, _, _, _, _ = create_manager(tmp_path)

    with pytest.raises(
        ValueError,
        match="Memory not found: missing",
    ):
        manager.deprecate("missing")


# ---------------------------------------------------------------------------
# SUPERSEDE
# ---------------------------------------------------------------------------


def test_supersede_replaces_active_index_entry(tmp_path):
    (
        manager,
        store,
        _,
        _,
        vector_store,
    ) = create_manager(tmp_path)

    old_memory = create_memory(
        memory_id="mem_old",
        title="Payment API Timeout",
        content="Old timeout procedure.",
    )

    manager.add(old_memory)

    new_memory = create_memory(
        memory_id="mem_new",
        title="Payment API Timeout - Updated",
        content="Updated timeout procedure.",
    )

    result = manager.supersede(
        old_memory_id="mem_old",
        new_memory=new_memory,
    )

    # New memory returned.
    assert result.memory_id == "mem_new"
    assert result.status == MemoryStatus.ACTIVE

    # New version is based on old version.
    assert result.version == 2

    # New memory points to old memory.
    assert result.relations.supersedes == [
        "mem_old"
    ]

    # Old memory is deprecated.
    old_saved = store.get("mem_old")

    assert old_saved is not None
    assert old_saved.status == MemoryStatus.DEPRECATED

    # New memory exists.
    new_saved = store.get("mem_new")

    assert new_saved is not None
    assert new_saved.status == MemoryStatus.ACTIVE
    assert new_saved.version == 2

    # Old vector entry removed.
    assert "mem_old" not in vector_store.items

    # New vector entry indexed.
    assert "mem_new" in vector_store.items

    assert "mem_old" in vector_store.delete_calls

    add_ids = [
        call["memory_id"]
        for call in vector_store.add_calls
    ]

    assert add_ids == [
        "mem_old",
        "mem_new",
    ]


def test_supersede_rejects_existing_new_memory(tmp_path):
    manager, _, _, _, _ = create_manager(tmp_path)

    old_memory = create_memory(
        memory_id="mem_old"
    )

    existing_memory = create_memory(
        memory_id="mem_new"
    )

    manager.add(old_memory)
    manager.add(existing_memory)

    replacement = create_memory(
        memory_id="mem_new",
        title="Another replacement",
    )

    with pytest.raises(
        ValueError,
        match="New memory already exists: mem_new",
    ):
        manager.supersede(
            old_memory_id="mem_old",
            new_memory=replacement,
        )


def test_supersede_rejects_missing_old_memory(tmp_path):
    manager, _, _, _, _ = create_manager(tmp_path)

    new_memory = create_memory(
        memory_id="mem_new"
    )

    with pytest.raises(
        ValueError,
        match="Memory not found: missing",
    ):
        manager.supersede(
            old_memory_id="missing",
            new_memory=new_memory,
        )


# ---------------------------------------------------------------------------
# MERGE
# ---------------------------------------------------------------------------


def test_merge_deprecates_source_and_reindexes_target(tmp_path):
    (
        manager,
        store,
        _,
        _,
        vector_store,
    ) = create_manager(tmp_path)

    target = create_memory(
        memory_id="mem_target",
        title="Payment API Timeout",
        tags=["payment", "timeout"],
    )

    target.importance.score = 0.5
    target.usage.mention_count = 2
    target.usage.retrieval_count = 3
    target.evidence.level = "medium"

    source = create_memory(
        memory_id="mem_source",
        title="Connection Pool Issue",
        tags=["database", "connection-pool"],
    )

    source.importance.score = 0.9
    source.usage.mention_count = 4
    source.usage.retrieval_count = 5
    source.evidence.level = "high"

    source.relations.related_to = [
        "mem_related"
    ]
    source.relations.supports = [
        "mem_target"
    ]
    source.evidence.references = [
        "INC-1042"
    ]

    manager.add(target)
    manager.add(source)

    result = manager.merge(
        target_memory_id="mem_target",
        source_memory_id="mem_source",
    )

    # Target returned.
    assert result.memory_id == "mem_target"

    # Target version incremented.
    assert result.version == 2

    # Tags merged.
    assert result.tags == [
        "payment",
        "timeout",
        "database",
        "connection-pool",
    ]

    # Source relation retained.
    assert "mem_related" in result.relations.related_to

    # Source memory becomes derived-from target.
    assert "mem_source" in result.relations.derived_from

    # Supports relation merged.
    assert "mem_target" in result.relations.supports

    # Evidence references merged.
    assert "INC-1042" in result.evidence.references

    # Stronger evidence wins.
    assert result.evidence.level == "high"

    # Highest importance wins.
    assert result.importance.score == pytest.approx(0.9)

    # Usage accumulated.
    assert result.usage.mention_count == 6
    assert result.usage.retrieval_count == 8

    # Source is deprecated.
    source_saved = store.get("mem_source")

    assert source_saved is not None
    assert source_saved.status == MemoryStatus.DEPRECATED

    # Target is still active.
    target_saved = store.get("mem_target")

    assert target_saved is not None
    assert target_saved.status == MemoryStatus.ACTIVE
    assert target_saved.version == 2

    # Source removed from vector index.
    assert "mem_source" not in vector_store.items

    # Target reindexed.
    assert "mem_target" in vector_store.items

    assert "mem_source" in vector_store.delete_calls

    # Target was initially indexed and then reindexed.
    target_adds = [
        call
        for call in vector_store.add_calls
        if call["memory_id"] == "mem_target"
    ]

    assert len(target_adds) == 2


def test_merge_rejects_same_memory_as_target_and_source(
    tmp_path,
):
    manager, _, _, _, _ = create_manager(tmp_path)

    memory = create_memory()

    manager.add(memory)

    with pytest.raises(
        ValueError,
        match="Target and source memory must be different",
    ):
        manager.merge(
            target_memory_id="mem_001",
            source_memory_id="mem_001",
        )


def test_merge_rejects_missing_target(tmp_path):
    manager, _, _, _, _ = create_manager(tmp_path)

    source = create_memory(
        memory_id="mem_source"
    )

    manager.add(source)

    with pytest.raises(
        ValueError,
        match="Memory not found: missing",
    ):
        manager.merge(
            target_memory_id="missing",
            source_memory_id="mem_source",
        )


def test_merge_rejects_missing_source(tmp_path):
    manager, _, _, _, _ = create_manager(tmp_path)

    target = create_memory(
        memory_id="mem_target"
    )

    manager.add(target)

    with pytest.raises(
        ValueError,
        match="Memory not found: missing",
    ):
        manager.merge(
            target_memory_id="mem_target",
            source_memory_id="missing",
        )


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------


def test_delete_removes_file_and_vector(tmp_path):
    (
        manager,
        store,
        _,
        _,
        vector_store,
    ) = create_manager(tmp_path)

    memory = create_memory()

    manager.add(memory)

    assert store.exists("mem_001")
    assert "mem_001" in vector_store.items

    manager.delete("mem_001")

    assert not store.exists("mem_001")
    assert store.get("mem_001") is None

    assert "mem_001" not in vector_store.items

    assert vector_store.delete_calls == [
        "mem_001"
    ]


def test_delete_missing_memory_fails(tmp_path):
    manager, _, _, _, vector_store = create_manager(tmp_path)

    with pytest.raises(
        ValueError,
        match="Memory not found: missing",
    ):
        manager.delete("missing")

    # Vector store should not be touched.
    assert vector_store.delete_calls == []


# ---------------------------------------------------------------------------
# MERGE helper behavior
# ---------------------------------------------------------------------------


def test_merge_does_not_duplicate_existing_tags(tmp_path):
    manager, store, _, _, _ = create_manager(tmp_path)

    target = create_memory(
        memory_id="mem_target",
        tags=[
            "payment",
            "timeout",
        ],
    )

    source = create_memory(
        memory_id="mem_source",
        tags=[
            "timeout",
            "database",
        ],
    )

    manager.add(target)
    manager.add(source)

    result = manager.merge(
        target_memory_id="mem_target",
        source_memory_id="mem_source",
    )

    assert result.tags == [
        "payment",
        "timeout",
        "database",
    ]


def test_merge_preserves_target_content(tmp_path):
    manager, store, _, _, _ = create_manager(tmp_path)

    target = create_memory(
        memory_id="mem_target",
        content="Target content.",
    )

    source = create_memory(
        memory_id="mem_source",
        content="Source content.",
    )

    manager.add(target)
    manager.add(source)

    result = manager.merge(
        target_memory_id="mem_target",
        source_memory_id="mem_source",
    )

    # Current MemoryManager semantics merge metadata/relations,
    # but do not concatenate content.
    assert result.content == "Target content."