from datetime import datetime, timezone
from pathlib import Path

from jarvis.memory.file_store import FileMemoryStore
from jarvis.memory.models import (
    Memory,
    MemoryEvidence,
    MemoryImportance,
    MemoryRelations,
    MemoryScope,
    MemorySource,
    MemoryType,
)


def create_memory() -> Memory:
    now = datetime.now(timezone.utc)

    return Memory(
        memory_id="mem_runbook_001",
        schema_version=1,
        memory_type=MemoryType.RUNBOOK,
        title="Payment API Timeout",
        domain="payments",
        category="incident",
        tags=["payment", "timeout"],
        scope=MemoryScope(
            owner="user",
            workspace="work",
            domain="software",
            project="payment-platform",
            service="payment-api",
            environment="production",
        ),
        created_at=now,
        updated_at=now,
        source=MemorySource(
            type="manual",
            ref="payment-operations",
        ),
        evidence=MemoryEvidence(
            level="high",
            references=["INC-1042"],
        ),
        importance=MemoryImportance(score=0.9),
        relations=MemoryRelations(),
        content="Diagnose and resolve payment API timeout issues.",
    )


def test_save_and_get(tmp_path: Path):
    store = FileMemoryStore(tmp_path)

    memory = create_memory()

    store.save(memory)

    loaded = store.get(memory.memory_id)

    assert loaded is not None
    assert loaded.memory_id == memory.memory_id
    assert loaded.title == memory.title
    assert loaded.memory_type == memory.memory_type
    assert loaded.content == memory.content
    assert loaded.tags == memory.tags


def test_exists(tmp_path: Path):
    store = FileMemoryStore(tmp_path)

    memory = create_memory()

    assert store.exists(memory.memory_id) is False

    store.save(memory)

    assert store.exists(memory.memory_id) is True


def test_delete(tmp_path: Path):
    store = FileMemoryStore(tmp_path)

    memory = create_memory()

    store.save(memory)

    assert store.exists(memory.memory_id) is True

    store.delete(memory.memory_id)

    assert store.exists(memory.memory_id) is False
    assert store.get(memory.memory_id) is None


def test_get_missing_memory(tmp_path: Path):
    store = FileMemoryStore(tmp_path)

    result = store.get("does-not-exist")

    assert result is None