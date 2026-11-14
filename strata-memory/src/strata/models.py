from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ============================================================================
# 1. LLM EXTRACTION & DECISION MODELS
# ============================================================================

class SemanticExtractionOp(BaseModel):
    action: Literal["ADD", "SUPERSEDE", "IGNORE"] = "ADD"
    supersede_memory_id: Optional[str] = None
    summary: str
    tags: List[str] = Field(default_factory=list)
    confidence: float = 1.0


class EpisodicExtractionOp(BaseModel):
    summary: str
    situation: str
    action_taken: str
    outcome: str
    success: bool = True
    tags: List[str] = Field(default_factory=list)


class ProceduralExtractionOp(BaseModel):
    action: Literal["CREATE", "UPDATE"] = "CREATE"
    name: str
    description: str
    trigger_condition: str
    steps: List[str] = Field(default_factory=list)
    prerequisites: Dict[str, Any] = Field(default_factory=dict)
    reason_for_change: Optional[str] = None


class EntityExtractionOp(BaseModel):
    source_name: str
    source_type: str = "concept"
    source_summary: str = ""
    relation_type: str
    target_name: str
    target_type: str = "concept"
    target_summary: str = ""
    fact_summary: str
    invalidate_conflicting_relations: bool = True


class MemoryExtractionPlan(BaseModel):
    semantic_ops: List[SemanticExtractionOp] = Field(default_factory=list)
    episodic_ops: List[EpisodicExtractionOp] = Field(default_factory=list)
    procedural_ops: List[ProceduralExtractionOp] = Field(default_factory=list)
    entity_ops: List[EntityExtractionOp] = Field(default_factory=list)


class ProcedurePatchPlan(BaseModel):
    name: str
    patched_steps: List[str]
    reason_for_patch: str


# ============================================================================
# 2. RECALL MODELS
# ============================================================================

class SemanticMemoryItem(BaseModel):
    memory_id: str
    summary: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    utility_score: int = 0
    confidence: float = 1.0
    created_at: datetime
    rrf_score: float = 0.0


class EpisodicMemoryItem(BaseModel):
    memory_id: str
    summary: str
    situation: Optional[str] = None
    action_taken: Optional[str] = None
    outcome: Optional[str] = None
    success: Optional[bool] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    utility_score: int = 0
    created_at: datetime
    rrf_score: float = 0.0


class ProceduralMemoryItem(BaseModel):
    procedure_id: str
    name: str
    description: str
    trigger_condition: str
    steps: List[str] = Field(default_factory=list)
    prerequisites: Dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    success_count: int = 0
    fail_count: int = 0
    success_rate: float = 0.5
    composite_score: float = 0.0


class EntityGraphItem(BaseModel):
    edge_id: str
    source_name: str
    source_type: str
    relation_type: str
    target_name: str
    target_type: str
    fact_summary: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    valid_from: datetime


class RecallRequest(BaseModel):
    query: str
    namespace: str = "default"
    pillars: List[str] = Field(default_factory=lambda: ["semantic", "episodic", "procedural", "entity"])
    top_k: int = 5
    token_budget: int = 1500
    match_threshold: Optional[float] = None
    min_score: Optional[float] = None
    similarity_threshold: Optional[float] = None


class RecallResponse(BaseModel):
    namespace: str
    query: str
    semantic: List[SemanticMemoryItem] = Field(default_factory=list)
    episodic: List[EpisodicMemoryItem] = Field(default_factory=list)
    procedural: List[ProceduralMemoryItem] = Field(default_factory=list)
    entities: List[EntityGraphItem] = Field(default_factory=list)
    formatted_context: str
    token_count_approx: int = 0


# ============================================================================
# 3. TOOL & API INTERACTION SCHEMAS
# ============================================================================

class IngestRequest(BaseModel):
    raw_text: str
    namespace: str = "default"
    fast_mode: bool = False
    source_id: Optional[str] = None
    ttl_seconds: Optional[int] = None
    contradiction_threshold: Optional[float] = None
    use_decision_model: Optional[bool] = None


class IngestResponse(BaseModel):
    success: bool
    namespace: str
    fast_mode: bool
    created_ids: List[str] = Field(default_factory=list)
    superseded_ids: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class StoreExplicitRequest(BaseModel):
    pillar: Literal["semantic", "episodic", "procedural", "entity"]
    payload: Dict[str, Any]
    ttl_seconds: Optional[int] = None
    namespace: str = "default"


class EditRequest(BaseModel):
    target_id_or_name: str
    instruction: str
    pillar: Literal["semantic", "procedural", "entity"] = "semantic"
    namespace: str = "default"


class FeedbackRequest(BaseModel):
    memory_ids_used: List[str] = Field(default_factory=list)
    procedure_name: Optional[str] = None
    success: bool = True
    failure_reason: Optional[str] = None
    namespace: str = "default"


class DeleteRequest(BaseModel):
    target_id: str
    pillar: Literal["semantic", "episodic", "procedural", "entity"] = "semantic"
    hard_delete: bool = False
    namespace: str = "default"


class DistilledSemanticFact(BaseModel):
    summary: str
    tags: List[str] = Field(default_factory=list)
    confidence: float = 1.0


class DistilledProcedure(BaseModel):
    name: str
    description: str
    trigger_condition: str
    steps: List[str] = Field(default_factory=list)


class MemoryDistillationPlan(BaseModel):
    has_durable_knowledge: bool = False
    semantic_facts: List[DistilledSemanticFact] = Field(default_factory=list)
    procedures: List[DistilledProcedure] = Field(default_factory=list)
    reasoning: str = ""


class PruneRequest(BaseModel):
    namespace: str = "default"
    distill_episodes: bool = True
    episodic_older_than_days: Optional[int] = 30
    superseded_older_than_days: int = 90
    retire_toxic_threshold: Optional[int] = -5
    batch_size: int = 20


class PruneResponse(BaseModel):
    namespace: str
    distilled_facts_created: int = 0
    distilled_procedures_created: int = 0
    episodes_pruned: int = 0
    superseded_pruned: int = 0
    toxic_memories_retired: int = 0
    details: Dict[str, Any] = Field(default_factory=dict)


class PurgeNamespaceRequest(BaseModel):
    namespace: str
    confirm: bool = False


class PurgeNamespaceResponse(BaseModel):
    namespace: str
    purged: bool
    deleted_counts: Dict[str, int] = Field(default_factory=dict)
