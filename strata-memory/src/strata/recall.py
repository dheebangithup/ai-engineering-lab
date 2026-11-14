import asyncio
import logging
from typing import List
from uuid import UUID

from strata.db import get_db_pool
from strata.embedder import LocalEmbedder
from strata.models import (
    EntityGraphItem,
    EpisodicMemoryItem,
    ProceduralMemoryItem,
    RecallRequest,
    RecallResponse,
    SemanticMemoryItem,
)
from strata.pillars.entity_graph import search_entity_subgraph
from strata.pillars.procedural import search_procedures

logger = logging.getLogger("strata.recall")


async def execute_hybrid_search(
    query_text: str,
    query_embedding: List[float],
    namespace: str,
    target_types: List[str],
    top_k: int,
) -> List[dict]:
    """Calls hybrid_memory_search SQL function in Neon Postgres."""
    pool = await get_db_pool()
    vec_str = LocalEmbedder.to_pgvector_str(query_embedding)

    async with pool.acquire() as c:
        rows = await c.fetch(
            """
            SELECT
                memory_id,
                type,
                summary,
                payload,
                tags,
                utility_score,
                confidence,
                created_at,
                rrf_score
            FROM hybrid_memory_search(
                $1,
                $2::vector(768),
                $3,
                $4,
                0.35,
                $5
            );
            """,
            query_text,
            vec_str,
            namespace,
            target_types,
            top_k * 2,
        )
        return [dict(r) for r in rows]


async def bump_access_counts(memory_ids: List[UUID]) -> None:
    """Asynchronously increments access_count for retrieved memories."""
    if not memory_ids:
        return
    try:
        pool = await get_db_pool()
        async with pool.acquire() as c:
            await c.execute(
                "UPDATE memories SET access_count = access_count + 1 WHERE memory_id = ANY($1::uuid[]);",
                memory_ids,
            )
    except Exception as exc:
        logger.debug(f"Failed to bump access count: {exc}")


def build_xml_context(
    namespace: str,
    semantic: List[SemanticMemoryItem],
    entities: List[EntityGraphItem],
    procedural: List[ProceduralMemoryItem],
    episodic: List[EpisodicMemoryItem],
    token_budget: int,
) -> str:
    """Builds a well-formed XML block constrained to the token_budget (len(text)//4)."""
    header = f'<strata_memory_context namespace="{namespace}">\n'
    footer = '</strata_memory_context>'

    available_chars = max(100, (token_budget * 4) - len(header) - len(footer) - 100)
    current_chars = 0

    # 1. Semantic facts
    sem_lines = []
    for s in semantic:
        line = f'    - [mem_id={s.memory_id[:8]}] {s.summary}'
        if current_chars + len(line) + 50 > available_chars:
            break
        sem_lines.append(line)
        current_chars += len(line) + 1

    # 2. Entity graph
    ent_lines = []
    for e in entities:
        line = f'    - ({e.source_name} [{e.source_type}]) -[{e.relation_type}]-> ({e.target_name} [{e.target_type}]): {e.fact_summary}'
        if current_chars + len(line) + 50 > available_chars:
            break
        ent_lines.append(line)
        current_chars += len(line) + 1

    # 3. Procedural skills
    proc_lines = []
    for p in procedural:
        rate_pct = int(p.success_rate * 100)
        steps_preview = " ".join(f"{i+1}. {step}" for i, step in enumerate(p.steps[:3]))
        line = f'    - [skill={p.name} v{p.version} | success_rate={rate_pct}%] Trigger: {p.trigger_condition}\n      Steps: {steps_preview}'
        if current_chars + len(line) + 50 > available_chars:
            break
        proc_lines.append(line)
        current_chars += len(line) + 1

    # 4. Episodic history
    epi_lines = []
    for ep in episodic:
        date_str = ep.created_at.strftime("%Y-%m-%d") if ep.created_at else "recent"
        status = "SUCCESS" if ep.success else "FAILURE"
        line = f'    - [{date_str} | outcome={status}] {ep.summary}'
        if current_chars + len(line) + 50 > available_chars:
            break
        epi_lines.append(line)
        current_chars += len(line) + 1

    # Assemble XML
    parts = [header]
    if sem_lines:
        parts.append("  <semantic_facts>\n" + "\n".join(sem_lines) + "\n  </semantic_facts>\n")
    if ent_lines:
        parts.append("  <entity_graph>\n" + "\n".join(ent_lines) + "\n  </entity_graph>\n")
    if proc_lines:
        parts.append("  <procedural_skills>\n" + "\n".join(proc_lines) + "\n  </procedural_skills>\n")
    if epi_lines:
        parts.append("  <episodic_history>\n" + "\n".join(epi_lines) + "\n  </episodic_history>\n")
    parts.append(footer)

    return "".join(parts)


async def memory_recall_internal(req: RecallRequest) -> RecallResponse:
    """Executes deterministic recall across requested pillars in a single round trip."""
    embedder = LocalEmbedder.get_instance()
    query_embedding = embedder.embed_one(req.query)

    pillars = set(req.pillars)
    tasks = []

    # 1. Semantic & Episodic search
    hybrid_types = []
    if "semantic" in pillars:
        hybrid_types.append("semantic")
    if "episodic" in pillars:
        hybrid_types.append("episodic")

    async def _fetch_hybrid():
        if not hybrid_types:
            return []
        return await execute_hybrid_search(
            query_text=req.query,
            query_embedding=query_embedding,
            namespace=req.namespace,
            target_types=hybrid_types,
            top_k=req.top_k,
        )

    # 2. Procedural search
    async def _fetch_procedural():
        if "procedural" not in pillars:
            return []
        return await search_procedures(
            query_embedding=query_embedding,
            namespace=req.namespace,
            top_k=req.top_k,
        )

    # 3. Entity subgraph search
    async def _fetch_entity():
        if "entity" not in pillars:
            return []
        return await search_entity_subgraph(
            query_embedding=query_embedding,
            query_text=req.query,
            namespace=req.namespace,
            top_k=req.top_k,
        )

    hybrid_res, procedural_res, entity_res = await asyncio.gather(
        _fetch_hybrid(),
        _fetch_procedural(),
        _fetch_entity(),
    )

    semantic_items: List[SemanticMemoryItem] = []
    episodic_items: List[EpisodicMemoryItem] = []
    retrieved_memory_uuids: List[UUID] = []

    for row in hybrid_res:
        mid_str = str(row["memory_id"])
        retrieved_memory_uuids.append(row["memory_id"])
        if row["type"] == "semantic":
            semantic_items.append(
                SemanticMemoryItem(
                    memory_id=mid_str,
                    summary=row["summary"],
                    payload=row["payload"] or {},
                    tags=row["tags"] or [],
                    utility_score=row["utility_score"],
                    confidence=row["confidence"],
                    created_at=row["created_at"],
                    rrf_score=row["rrf_score"],
                )
            )
        elif row["type"] == "episodic":
            payload = row["payload"] or {}
            episodic_items.append(
                EpisodicMemoryItem(
                    memory_id=mid_str,
                    summary=row["summary"],
                    situation=payload.get("situation"),
                    action_taken=payload.get("action_taken"),
                    outcome=payload.get("outcome"),
                    success=payload.get("success"),
                    payload=payload,
                    tags=row["tags"] or [],
                    utility_score=row["utility_score"],
                    created_at=row["created_at"],
                    rrf_score=row["rrf_score"],
                )
            )

    # Sort each pillar by score
    semantic_items.sort(key=lambda x: x.rrf_score, reverse=True)
    episodic_items.sort(key=lambda x: x.rrf_score, reverse=True)
    procedural_items = procedural_res[:req.top_k]
    entity_items = entity_res[:req.top_k]

    # Asynchronously bump access counts
    asyncio.create_task(bump_access_counts(retrieved_memory_uuids))

    # Build XML context
    formatted_context = build_xml_context(
        namespace=req.namespace,
        semantic=semantic_items[:req.top_k],
        entities=entity_items,
        procedural=procedural_items,
        episodic=episodic_items[:req.top_k],
        token_budget=req.token_budget,
    )

    token_approx = len(formatted_context) // 4

    return RecallResponse(
        namespace=req.namespace,
        query=req.query,
        semantic=semantic_items[:req.top_k],
        episodic=episodic_items[:req.top_k],
        procedural=procedural_items,
        entities=entity_items,
        formatted_context=formatted_context,
        token_count_approx=token_approx,
    )
