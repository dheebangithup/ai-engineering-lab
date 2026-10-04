from datetime import datetime

from jarvis.memory.models import (
    Memory,
    MemoryEvidence,
    MemoryImportance,
    MemoryRelations,
    MemoryScope,
    MemorySource,
    MemoryStatus,
    MemoryType,
    MemoryUsage,
)


def memory_to_dict(memory: Memory) -> dict:
    return {
        "memory_id": memory.memory_id,
        "schema_version": memory.schema_version,
        "memory_type": memory.memory_type.value,
        "title": memory.title,

        "domain": memory.domain,
        "category": memory.category,
        "tags": memory.tags,

        "scope": {
            "owner": memory.scope.owner,
            "workspace": memory.scope.workspace,
            "domain": memory.scope.domain,
            "project": memory.scope.project,
            "service": memory.scope.service,
            "environment": memory.scope.environment,
            "team": memory.scope.team,
        },

        "status": memory.status.value,
        "version": memory.version,

        "created_at": _datetime_to_string(memory.created_at),
        "updated_at": _datetime_to_string(memory.updated_at),
        "valid_from": _datetime_to_string(memory.valid_from),
        "valid_until": _datetime_to_string(memory.valid_until),

        "source": (
            {
                "type": memory.source.type,
                "ref": memory.source.ref,
            }
            if memory.source
            else None
        ),

        "evidence": {
            "level": memory.evidence.level,
            "references": memory.evidence.references,
        },

        "importance": {
            "score": memory.importance.score,
        },

        "usage": {
            "retrieval_count": memory.usage.retrieval_count,
            "mention_count": memory.usage.mention_count,
            "last_retrieved_at": _datetime_to_string(
                memory.usage.last_retrieved_at
            ),
        },

        "relations": {
            "related_to": memory.relations.related_to,
            "derived_from": memory.relations.derived_from,
            "supersedes": memory.relations.supersedes,
            "supports": memory.relations.supports,
        },

        "content": memory.content,
    }


def memory_from_dict(data: dict) -> Memory:
    scope_data = data.get("scope", {})
    source_data = data.get("source")
    evidence_data = data.get("evidence", {})
    importance_data = data.get("importance", {})
    usage_data = data.get("usage", {})
    relations_data = data.get("relations", {})

    return Memory(
        memory_id=data["memory_id"],
        schema_version=data["schema_version"],
        memory_type=MemoryType(data["memory_type"]),
        title=data["title"],

        domain=data.get("domain"),
        category=data.get("category"),
        tags=data.get("tags", []),

        scope=MemoryScope(
            owner=scope_data.get("owner", "user"),
            workspace=scope_data.get("workspace"),
            domain=scope_data.get("domain"),
            project=scope_data.get("project"),
            service=scope_data.get("service"),
            environment=scope_data.get("environment"),
            team=scope_data.get("team"),
        ),

        status=MemoryStatus(
            data.get("status", MemoryStatus.ACTIVE.value)
        ),
        version=data.get("version", 1),

        created_at=_datetime_from_string(data.get("created_at")),
        updated_at=_datetime_from_string(data.get("updated_at")),
        valid_from=_datetime_from_string(data.get("valid_from")),
        valid_until=_datetime_from_string(data.get("valid_until")),

        source=(
            MemorySource(
                type=source_data["type"],
                ref=source_data.get("ref"),
            )
            if source_data
            else None
        ),

        evidence=MemoryEvidence(
            level=evidence_data.get("level", "low"),
            references=evidence_data.get("references", []),
        ),

        importance=MemoryImportance(
            score=importance_data.get("score", 0.0),
        ),

        usage=MemoryUsage(
            retrieval_count=usage_data.get("retrieval_count", 0),
            mention_count=usage_data.get("mention_count", 0),
            last_retrieved_at=_datetime_from_string(
                usage_data.get("last_retrieved_at")
            ),
        ),

        relations=MemoryRelations(
            related_to=relations_data.get("related_to", []),
            derived_from=relations_data.get("derived_from", []),
            supersedes=relations_data.get("supersedes", []),
            supports=relations_data.get("supports", []),
        ),

        content=data.get("content", ""),
    )


def _datetime_to_string(value: datetime | None) -> str | None:
    if value is None:
        return None

    return value.isoformat()


def _datetime_from_string(value: str | None) -> datetime | None:
    if value is None:
        return None

    return datetime.fromisoformat(value)