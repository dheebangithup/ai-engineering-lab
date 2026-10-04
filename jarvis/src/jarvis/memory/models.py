from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class MemoryType(str, Enum):
    RUNBOOK = "runbook"
    LESSON = "lesson"


class MemoryStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class MemoryOperation(str, Enum):
    ADD = "add"
    MERGE = "merge"
    REINFORCE = "reinforce"
    SUPERSEDE = "supersede"
    DEPRECATE = "deprecate"


@dataclass
class MemoryScope:
    owner: str = "user"
    workspace: str | None = None
    domain: str | None = None
    project: str | None = None
    service: str | None = None
    environment: str | None = None
    team: str | None = None


@dataclass
class MemorySource:
    type: str
    ref: str | None = None


@dataclass
class MemoryEvidence:
    level: str = "low"
    references: list[str] = field(default_factory=list)


@dataclass
class MemoryImportance:
    score: float = 0.0


@dataclass
class MemoryUsage:
    retrieval_count: int = 0
    mention_count: int = 0
    last_retrieved_at: datetime | None = None


@dataclass
class MemoryRelations:
    related_to: list[str] = field(default_factory=list)
    derived_from: list[str] = field(default_factory=list)
    supersedes: list[str] = field(default_factory=list)
    supports: list[str] = field(default_factory=list)


@dataclass
class Memory:
    memory_id: str
    schema_version: int
    memory_type: MemoryType
    title: str

    domain: str | None = None
    category: str | None = None
    tags: list[str] = field(default_factory=list)

    scope: MemoryScope = field(default_factory=MemoryScope)

    status: MemoryStatus = MemoryStatus.ACTIVE
    version: int = 1

    created_at: datetime | None = None
    updated_at: datetime | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None

    source: MemorySource | None = None
    evidence: MemoryEvidence = field(default_factory=MemoryEvidence)

    importance: MemoryImportance = field(
        default_factory=MemoryImportance
    )

    usage: MemoryUsage = field(default_factory=MemoryUsage)

    relations: MemoryRelations = field(
        default_factory=MemoryRelations
    )

    content: str = ""