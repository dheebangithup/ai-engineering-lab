from datetime import datetime, timezone

from jarvis.memory.embedding_engine import EmbeddingProvider
from jarvis.memory.file_store import FileMemoryStore
from jarvis.memory.models import (
    Memory,
    MemoryStatus,
)
from jarvis.memory.vector_store import VectorStore
from jarvis.memory.vector_store.sparse_encoder import SparseEncoder


class MemoryManager:
    def __init__(
        self,
        store: FileMemoryStore,
        embedding_provider: EmbeddingProvider,
        sparse_encoder: SparseEncoder,
        vector_store: VectorStore,
    ):
        self._store = store
        self._embedding_provider = embedding_provider
        self._sparse_encoder = sparse_encoder
        self._vector_store = vector_store

    # ------------------------------------------------------------------
    # ADD
    # ------------------------------------------------------------------

    def add(self, memory: Memory) -> Memory:
        if self._store.exists(memory.memory_id):
            raise ValueError(
                f"Memory already exists: {memory.memory_id}"
            )

        now = self._now()

        memory.created_at = memory.created_at or now
        memory.updated_at = now

        # Persist canonical memory first.
        self._store.save(memory)

        # Add to retrieval index.
        self._index_memory(memory)

        return memory

    # ------------------------------------------------------------------
    # GET
    # ------------------------------------------------------------------

    def get(self, memory_id: str) -> Memory | None:
        return self._store.get(memory_id)

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def delete(self, memory_id: str) -> None:
        self._require_memory(memory_id)

        self._store.delete(memory_id)
        self._delete_from_index(memory_id)

    # ------------------------------------------------------------------
    # REINFORCE
    # ------------------------------------------------------------------

    def reinforce(
        self,
        memory_id: str,
        importance_delta: float = 0.1,
    ) -> Memory:
        memory = self._require_memory(memory_id)

        memory.importance.score = min(
            1.0,
            memory.importance.score + importance_delta,
        )

        memory.usage.mention_count += 1
        memory.updated_at = self._now()

        self._store.save(memory)

        # Only metadata changed.
        # Semantic representation did not change,
        # so no embedding regeneration is necessary.
        self._update_index_payload(memory)

        return memory

    # ------------------------------------------------------------------
    # MERGE
    # ------------------------------------------------------------------

    def merge(
        self,
        target_memory_id: str,
        source_memory_id: str,
    ) -> Memory:
        if target_memory_id == source_memory_id:
            raise ValueError(
                "Target and source memory must be different"
            )

        target = self._require_memory(
            target_memory_id
        )

        source = self._require_memory(
            source_memory_id
        )

        # --------------------------------------------------------------
        # Merge metadata
        # --------------------------------------------------------------

        target.tags = self._merge_unique(
            target.tags,
            source.tags,
        )

        target.relations.related_to = (
            self._merge_unique(
                target.relations.related_to,
                source.relations.related_to,
            )
        )

        target.relations.derived_from = (
            self._merge_unique(
                target.relations.derived_from,
                source.relations.derived_from,
            )
        )

        target.relations.supports = (
            self._merge_unique(
                target.relations.supports,
                source.relations.supports,
            )
        )

        # Source contributed to the surviving target.
        target.relations.derived_from = (
            self._merge_unique(
                target.relations.derived_from,
                [source.memory_id],
            )
        )

        target.evidence.references = (
            self._merge_unique(
                target.evidence.references,
                source.evidence.references,
            )
        )

        target.evidence.level = (
            self._stronger_evidence_level(
                target.evidence.level,
                source.evidence.level,
            )
        )

        target.importance.score = max(
            target.importance.score,
            source.importance.score,
        )

        target.usage.mention_count += (
            source.usage.mention_count
        )

        target.usage.retrieval_count += (
            source.usage.retrieval_count
        )

        # --------------------------------------------------------------
        # Lifecycle
        # --------------------------------------------------------------

        now = self._now()

        target.version += 1
        target.updated_at = now

        source.status = MemoryStatus.DEPRECATED
        source.updated_at = now

        # --------------------------------------------------------------
        # Persist canonical memories
        # --------------------------------------------------------------

        self._store.save(target)
        self._store.save(source)

        # --------------------------------------------------------------
        # Update retrieval index
        # --------------------------------------------------------------

        # Source should no longer participate in active retrieval.
        self._delete_from_index(
            source.memory_id
        )

        # Target semantic representation changed,
        # therefore regenerate its vectors.
        self._index_memory(target)

        return target

    # ------------------------------------------------------------------
    # SUPERSEDE
    # ------------------------------------------------------------------

    def supersede(
        self,
        old_memory_id: str,
        new_memory: Memory,
    ) -> Memory:
        old_memory = self._require_memory(
            old_memory_id
        )

        if self._store.exists(
            new_memory.memory_id
        ):
            raise ValueError(
                f"New memory already exists: "
                f"{new_memory.memory_id}"
            )

        now = self._now()

        # --------------------------------------------------------------
        # New memory lifecycle
        # --------------------------------------------------------------

        new_memory.version = (
            old_memory.version + 1
        )

        new_memory.created_at = (
            new_memory.created_at or now
        )

        new_memory.updated_at = now
        new_memory.status = MemoryStatus.ACTIVE

        # New memory supersedes old memory.
        new_memory.relations.supersedes = (
            self._merge_unique(
                new_memory.relations.supersedes,
                [old_memory.memory_id],
            )
        )

        # Keep reverse provenance on the old memory.
        old_memory.relations.supersedes = (
            self._merge_unique(
                old_memory.relations.supersedes,
                [new_memory.memory_id],
            )
        )

        old_memory.status = MemoryStatus.DEPRECATED
        old_memory.updated_at = now

        # --------------------------------------------------------------
        # Persist canonical memories
        # --------------------------------------------------------------

        self._store.save(old_memory)
        self._store.save(new_memory)

        # --------------------------------------------------------------
        # Update retrieval index
        # --------------------------------------------------------------

        self._delete_from_index(
            old_memory.memory_id
        )

        self._index_memory(new_memory)

        return new_memory

    # ------------------------------------------------------------------
    # DEPRECATE
    # ------------------------------------------------------------------

    def deprecate(
        self,
        memory_id: str,
    ) -> Memory:
        memory = self._require_memory(
            memory_id
        )

        memory.status = MemoryStatus.DEPRECATED
        memory.updated_at = self._now()

        self._store.save(memory)

        # Deprecated memories should not participate
        # in normal retrieval.
        self._delete_from_index(
            memory_id
        )

        return memory

    # ------------------------------------------------------------------
    # INTERNAL
    # ------------------------------------------------------------------

    def _require_memory(
        self,
        memory_id: str,
    ) -> Memory:
        memory = self._store.get(memory_id)

        if memory is None:
            raise ValueError(
                f"Memory not found: {memory_id}"
            )

        return memory

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _merge_unique(
        first: list[str],
        second: list[str],
    ) -> list[str]:
        result = list(first)

        for item in second:
            if item not in result:
                result.append(item)

        return result

    @staticmethod
    def _stronger_evidence_level(
        first: str,
        second: str,
    ) -> str:
        levels = {
            "low": 1,
            "medium": 2,
            "high": 3,
        }

        if levels.get(second, 0) > levels.get(first, 0):
            return second

        return first

    # ------------------------------------------------------------------
    # Retrieval index
    # ------------------------------------------------------------------

    def _index_memory(
        self,
        memory: Memory,
    ) -> None:
        embedding_text = (
            self._build_embedding_text(memory)
        )

        dense_vector = (
            self._embedding_provider.embed(
                embedding_text
            )
        )

        sparse_vector = (
            self._sparse_encoder.encode(
                embedding_text
            )
        )

        self._vector_store.add(
            memory_id=memory.memory_id,
            dense_vector=dense_vector,
            sparse_vector=sparse_vector,
            payload=self._build_vector_payload(
                memory
            ),
        )

    def _update_index_payload(
        self,
        memory: Memory,
    ) -> None:
        self._vector_store.update(
            memory_id=memory.memory_id,
            payload=self._build_vector_payload(
                memory
            ),
        )

    def _delete_from_index(
        self,
        memory_id: str,
    ) -> None:
        self._vector_store.delete(
            memory_id
        )

    # ------------------------------------------------------------------
    # Embedding representation
    # ------------------------------------------------------------------

    @staticmethod
    def _build_embedding_text(
        memory: Memory,
    ) -> str:
        parts = [
            memory.title,
            memory.domain or "",
            memory.category or "",
            " ".join(memory.tags),
            memory.content,
        ]

        return "\n".join(
            part.strip()
            for part in parts
            if part and part.strip()
        )

    # ------------------------------------------------------------------
    # Vector payload
    # ------------------------------------------------------------------

    @staticmethod
    def _build_vector_payload(
        memory: Memory,
    ) -> dict:
        return {
            "memory_id": memory.memory_id,
            "memory_type": memory.memory_type.value,
            "title": memory.title,
            "domain": memory.domain,
            "category": memory.category,
            "tags": memory.tags,
            "status": memory.status.value,
            "version": memory.version,
        }