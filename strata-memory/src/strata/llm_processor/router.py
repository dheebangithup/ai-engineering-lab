import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI

from strata.config import settings
from strata.db import get_db_pool
from strata.embedder import LocalEmbedder
from strata.llm_processor.prompts import (
    EDIT_INSTRUCTION_PROMPT,
    EXTRACTION_SYSTEM_PROMPT,
    PROCEDURE_PATCH_PROMPT,
)
from strata.models import (
    IngestResponse,
    MemoryExtractionPlan,
    ProcedurePatchPlan,
)
from strata.pillars.entity_graph import upsert_entity_link
from strata.pillars.episodic import record_episode
from strata.pillars.procedural import upsert_procedure
from strata.pillars.semantic import add_or_supersede_semantic

logger = logging.getLogger("strata.llm_router")


def get_llm_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=settings.memory_llm_base_url,
        api_key=settings.memory_llm_api_key,
        timeout=settings.memory_llm_timeout_seconds,
    )


async def prefetch_relevant_context(
    raw_text: str,
    raw_embedding: List[float],
    namespace: str,
) -> Dict[str, Any]:
    """Prefetches existing similar memories, procedures, and entities to feed into the extraction LLM."""
    pool = await get_db_pool()
    vec_str = LocalEmbedder.to_pgvector_str(raw_embedding)

    async with pool.acquire() as c:
        # 1. Top active semantic memories
        sem_rows = await c.fetch(
            """
            SELECT memory_id, summary, tags
            FROM memories
            WHERE namespace = $1
              AND type = 'semantic'
              AND valid_until IS NULL
            ORDER BY (embedding <=> $2::vector(768)) ASC
            LIMIT 5;
            """,
            namespace,
            vec_str,
        )

        # 2. Top procedures
        proc_rows = await c.fetch(
            """
            SELECT name, trigger_condition, steps
            FROM procedural_memories
            WHERE namespace = $1 AND is_active = TRUE
            ORDER BY (trigger_embedding <=> $2::vector(768)) ASC
            LIMIT 3;
            """,
            namespace,
            vec_str,
        )

        # 3. Top entity nodes
        ent_rows = await c.fetch(
            """
            SELECT name, entity_type, summary
            FROM entity_nodes
            WHERE namespace = $1
            ORDER BY (embedding <=> $2::vector(768)) ASC
            LIMIT 5;
            """,
            namespace,
            vec_str,
        )

    return {
        "existing_semantic_memories": [
            {"id": str(r["memory_id"]), "summary": r["summary"], "tags": r["tags"]}
            for r in sem_rows
        ],
        "existing_procedures": [
            {"name": r["name"], "trigger": r["trigger_condition"], "steps": r["steps"]}
            for r in proc_rows
        ],
        "existing_entities": [
            {"name": r["name"], "type": r["entity_type"], "summary": r["summary"]}
            for r in ent_rows
        ],
    }


def clean_and_parse_json(content: str) -> dict:
    """Robustly parses JSON even if wrapped in thinking tags or markdown code fences."""
    text = content.strip()
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())


async def fallback_deterministic_ingest(
    raw_text: str,
    namespace: str,
    source_id: Optional[str] = None,
    embedding: Optional[List[float]] = None,
) -> IngestResponse:
    """Zero-LLM fallback: stores raw_text directly as a semantic memory item."""
    logger.info("Using deterministic fallback storage for ingest.")
    mem_id, superseded_id = await add_or_supersede_semantic(
        summary=raw_text.strip(),
        namespace=namespace,
        payload={"raw_fallback": True},
        source_id=source_id,
        embedding=embedding,
    )
    return IngestResponse(
        success=True,
        namespace=namespace,
        fast_mode=True,
        created_ids=[mem_id],
        superseded_ids=[superseded_id] if superseded_id else [],
        details={"mode": "deterministic_fallback", "pillar": "semantic"},
    )


async def process_and_ingest(
    raw_text: str,
    namespace: str = "default",
    fast_mode: bool = False,
    source_id: Optional[str] = None,
) -> IngestResponse:
    """Routes incoming raw text across the 4 memory pillars using a Small Decision LLM,
    or falls back cleanly to deterministic storage."""
    embedder = LocalEmbedder.get_instance()
    raw_embedding = embedder.embed_one(raw_text)

    if fast_mode or not settings.memory_llm_enabled:
        return await fallback_deterministic_ingest(
            raw_text=raw_text,
            namespace=namespace,
            source_id=source_id,
            embedding=raw_embedding,
        )

    try:
        # Step 1: Prefetch similar memories
        context_data = await prefetch_relevant_context(raw_text, raw_embedding, namespace)

        # Step 2: Call Small LLM
        client = get_llm_client()
        user_prompt = f"""EXISTING_SIMILAR_MEMORIES:
{json.dumps(context_data, indent=2)}

NEW_RAW_INPUT:
{raw_text}
"""
        response = await client.chat.completions.create(
            model=settings.memory_llm_model,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        content = response.choices[0].message.content or "{}"
        parsed = clean_and_parse_json(content)
        plan = MemoryExtractionPlan.model_validate(parsed)

        # If LLM returned empty plan, fall back to adding raw text as semantic
        if (
            not plan.semantic_ops
            and not plan.episodic_ops
            and not plan.procedural_ops
            and not plan.entity_ops
        ):
            return await fallback_deterministic_ingest(
                raw_text, namespace, source_id, raw_embedding
            )

        # Step 3: Execute plan across the 4 pillars in Neon Postgres
        pool = await get_db_pool()
        created_ids: List[str] = []
        superseded_ids: List[str] = []

        async with pool.acquire() as conn:
            async with conn.transaction():
                # 3.1 Semantic operations
                for sem in plan.semantic_ops:
                    if sem.action == "IGNORE":
                        continue
                    new_id, sup_id = await add_or_supersede_semantic(
                        summary=sem.summary,
                        namespace=namespace,
                        tags=sem.tags,
                        confidence=sem.confidence,
                        source_id=source_id,
                        supersede_memory_id=sem.supersede_memory_id if sem.action == "SUPERSEDE" else None,
                        conn=conn,
                    )
                    created_ids.append(new_id)
                    if sup_id:
                        superseded_ids.append(sup_id)

                # 3.2 Episodic operations
                for ep in plan.episodic_ops:
                    ep_id = await record_episode(
                        summary=ep.summary,
                        situation=ep.situation,
                        action_taken=ep.action_taken,
                        outcome=ep.outcome,
                        success=ep.success,
                        namespace=namespace,
                        tags=ep.tags,
                        source_id=source_id,
                        conn=conn,
                    )
                    created_ids.append(ep_id)

                # 3.3 Procedural operations
                for proc in plan.procedural_ops:
                    proc_id = await upsert_procedure(
                        name=proc.name,
                        description=proc.description,
                        trigger_condition=proc.trigger_condition,
                        steps=proc.steps,
                        prerequisites=proc.prerequisites,
                        namespace=namespace,
                        reason_for_change=proc.reason_for_change,
                        conn=conn,
                    )
                    created_ids.append(proc_id)

                # 3.4 Entity Graph operations
                for ent in plan.entity_ops:
                    edge_id = await upsert_entity_link(
                        source_name=ent.source_name,
                        source_type=ent.source_type,
                        source_summary=ent.source_summary,
                        relation_type=ent.relation_type,
                        target_name=ent.target_name,
                        target_type=ent.target_type,
                        target_summary=ent.target_summary,
                        fact_summary=ent.fact_summary,
                        invalidate_conflicting_relations=ent.invalidate_conflicting_relations,
                        namespace=namespace,
                        conn=conn,
                    )
                    created_ids.append(edge_id)

        return IngestResponse(
            success=True,
            namespace=namespace,
            fast_mode=False,
            created_ids=created_ids,
            superseded_ids=superseded_ids,
            details={
                "semantic_count": len(plan.semantic_ops),
                "episodic_count": len(plan.episodic_ops),
                "procedural_count": len(plan.procedural_ops),
                "entity_count": len(plan.entity_ops),
            },
        )

    except Exception as exc:
        logger.warning(
            f"Memory LLM processing failed or timed out ({exc}). Engaging deterministic fallback."
        )
        return await fallback_deterministic_ingest(
            raw_text=raw_text,
            namespace=namespace,
            source_id=source_id,
            embedding=raw_embedding,
        )


async def patch_procedure_with_llm(
    name: str,
    current_steps: List[str],
    failure_reason: str,
) -> Optional[List[str]]:
    """Uses the Small LLM to analyze a failure reason and suggest patched steps."""
    if not settings.memory_llm_enabled:
        return None

    try:
        client = get_llm_client()
        user_prompt = f"""Procedure Name: {name}
Current Steps: {json.dumps(current_steps)}
Failure Reason / Error: {failure_reason}
"""
        response = await client.chat.completions.create(
            model=settings.memory_llm_model,
            messages=[
                {"role": "system", "content": PROCEDURE_PATCH_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        content = response.choices[0].message.content or "{}"
        parsed = clean_and_parse_json(content)
        patch = ProcedurePatchPlan.model_validate(parsed)
        return patch.patched_steps
    except Exception as exc:
        logger.warning(f"Procedure patching via LLM failed ({exc}).")
        return None
