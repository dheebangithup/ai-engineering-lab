import json
import logging
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from strata.config import settings
from strata.db import get_db_pool
from strata.llm_processor.prompts import EDIT_INSTRUCTION_PROMPT
from strata.llm_processor.router import (
    get_llm_client,
    patch_procedure_with_llm,
    process_and_ingest,
)
from strata.models import (
    DeleteRequest,
    EditRequest,
    FeedbackRequest,
    IngestRequest,
    IngestResponse,
    RecallRequest,
    RecallResponse,
    StoreExplicitRequest,
)
from strata.pillars.entity_graph import (
    delete_entity,
    upsert_entity_link,
)
from strata.pillars.episodic import (
    delete_episodic,
    record_episode,
    update_utility_scores,
)
from strata.pillars.procedural import (
    delete_procedure,
    record_procedure_feedback,
    upsert_procedure,
)
from strata.pillars.semantic import (
    add_or_supersede_semantic,
    delete_semantic,
)
from strata.recall import memory_recall_internal

logger = logging.getLogger("strata.service")


async def svc_memory_ingest(
    raw_text: str,
    namespace: str = "default",
    fast_mode: bool = False,
    source_id: Optional[str] = None,
) -> IngestResponse:
    """Autonomous 4-pillar extraction & storage using the Memory-Side Small LLM."""
    return await process_and_ingest(
        raw_text=raw_text,
        namespace=namespace,
        fast_mode=fast_mode,
        source_id=source_id,
    )


async def svc_memory_recall(
    query: str,
    namespace: str = "default",
    pillars: Optional[List[str]] = None,
    top_k: int = 5,
    token_budget: int = 1500,
) -> RecallResponse:
    """Zero-LLM deterministic hybrid RRF + graph + procedural retrieval."""
    if pillars is None:
        pillars = ["semantic", "episodic", "procedural", "entity"]
    req = RecallRequest(
        query=query,
        namespace=namespace,
        pillars=pillars,
        top_k=top_k,
        token_budget=token_budget,
    )
    return await memory_recall_internal(req)


async def svc_memory_store_explicit(
    pillar: Literal["semantic", "episodic", "procedural", "entity"],
    payload: Dict[str, Any],
    namespace: str = "default",
) -> Dict[str, Any]:
    """Direct, zero-LLM structured write to any of the 4 pillars."""
    if pillar == "semantic":
        mem_id, superseded_id = await add_or_supersede_semantic(
            summary=payload.get("summary", ""),
            namespace=namespace,
            payload=payload.get("payload", {}),
            tags=payload.get("tags", []),
            confidence=float(payload.get("confidence", 1.0)),
            source_id=payload.get("source_id"),
            supersede_memory_id=payload.get("supersede_memory_id"),
        )
        return {"status": "stored", "pillar": "semantic", "memory_id": mem_id, "superseded_id": superseded_id}

    elif pillar == "episodic":
        ep_id = await record_episode(
            summary=payload.get("summary", ""),
            situation=payload.get("situation"),
            action_taken=payload.get("action_taken"),
            outcome=payload.get("outcome"),
            success=bool(payload.get("success", True)),
            namespace=namespace,
            tags=payload.get("tags", []),
            extra_payload=payload.get("extra_payload"),
            source_id=payload.get("source_id"),
        )
        return {"status": "stored", "pillar": "episodic", "memory_id": ep_id}

    elif pillar == "procedural":
        proc_id = await upsert_procedure(
            name=payload.get("name", "unnamed_procedure"),
            description=payload.get("description", ""),
            trigger_condition=payload.get("trigger_condition", ""),
            steps=payload.get("steps", []),
            prerequisites=payload.get("prerequisites", {}),
            namespace=namespace,
            reason_for_change=payload.get("reason_for_change", "Explicitly stored"),
        )
        return {"status": "stored", "pillar": "procedural", "procedure_id": proc_id}

    elif pillar == "entity":
        edge_id = await upsert_entity_link(
            source_name=payload.get("source_name", ""),
            source_type=payload.get("source_type", "concept"),
            source_summary=payload.get("source_summary", ""),
            relation_type=payload.get("relation_type", "RELATED_TO"),
            target_name=payload.get("target_name", ""),
            target_type=payload.get("target_type", "concept"),
            target_summary=payload.get("target_summary", ""),
            fact_summary=payload.get("fact_summary", ""),
            properties=payload.get("properties", {}),
            invalidate_conflicting_relations=payload.get("invalidate_conflicting_relations", True),
            namespace=namespace,
        )
        return {"status": "stored", "pillar": "entity", "edge_id": edge_id}

    else:
        raise ValueError(f"Unknown pillar: {pillar}")


async def svc_memory_edit(
    target_id_or_name: str,
    instruction: str,
    pillar: Literal["semantic", "procedural", "entity"] = "semantic",
    namespace: str = "default",
) -> Dict[str, Any]:
    """Uses the Memory-Side Small LLM to modify or supersede an existing memory."""
    pool = await get_db_pool()

    if pillar == "semantic":
        # Fetch existing memory
        try:
            target_uuid = UUID(target_id_or_name)
        except ValueError:
            return {"status": "error", "message": f"Invalid UUID: {target_id_or_name}"}

        async with pool.acquire() as c:
            existing = await c.fetchrow(
                "SELECT summary, tags, payload FROM memories WHERE memory_id = $1 AND namespace = $2 AND valid_until IS NULL",
                target_uuid,
                namespace,
            )

        if not existing:
            return {"status": "not_found", "message": f"No active semantic memory found with id {target_id_or_name}"}

        current_summary = existing["summary"]
        current_tags = existing["tags"] or []

        # If LLM enabled, re-write summary based on instruction
        new_summary = f"{current_summary} (Updated: {instruction})"
        new_tags = current_tags
        if settings.memory_llm_enabled:
            try:
                client = get_llm_client()
                resp = await client.chat.completions.create(
                    model=settings.memory_llm_model,
                    messages=[
                        {"role": "system", "content": EDIT_INSTRUCTION_PROMPT},
                        {
                            "role": "user",
                            "content": f"Existing Fact: {current_summary}\nExisting Tags: {current_tags}\nModification Instruction: {instruction}",
                        },
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                parsed = json.loads(resp.choices[0].message.content or "{}")
                if parsed.get("updated_summary"):
                    new_summary = parsed["updated_summary"]
                if parsed.get("updated_tags"):
                    new_tags = parsed["updated_tags"]
            except Exception as e:
                logger.warning(f"LLM edit failed ({e}), using default format.")

        # Supersede old memory with new fact
        new_id, superseded_id = await add_or_supersede_semantic(
            summary=new_summary,
            namespace=namespace,
            payload=existing["payload"] or {},
            tags=new_tags,
            supersede_memory_id=target_id_or_name,
        )
        return {
            "status": "edited",
            "pillar": "semantic",
            "new_memory_id": new_id,
            "superseded_memory_id": superseded_id,
            "summary": new_summary,
        }

    elif pillar == "procedural":
        async with pool.acquire() as c:
            existing = await c.fetchrow(
                "SELECT name, description, trigger_condition, steps, prerequisites FROM procedural_memories WHERE (name = $1 OR procedure_id::text = $1) AND namespace = $2 AND is_active = TRUE",
                target_id_or_name,
                namespace,
            )
        if not existing:
            return {"status": "not_found", "message": f"No active procedure found matching {target_id_or_name}"}

        name = existing["name"]
        steps = existing["steps"] if isinstance(existing["steps"], list) else []
        new_steps = steps + [f"Instruction: {instruction}"]

        if settings.memory_llm_enabled:
            try:
                client = get_llm_client()
                resp = await client.chat.completions.create(
                    model=settings.memory_llm_model,
                    messages=[
                        {"role": "system", "content": EDIT_INSTRUCTION_PROMPT},
                        {
                            "role": "user",
                            "content": f"Procedure: {name}\nCurrent Steps: {json.dumps(steps)}\nInstruction: {instruction}",
                        },
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                parsed = json.loads(resp.choices[0].message.content or "{}")
                if parsed.get("updated_steps"):
                    new_steps = parsed["updated_steps"]
            except Exception as e:
                logger.warning(f"LLM procedural edit failed ({e}).")

        proc_id = await upsert_procedure(
            name=name,
            description=existing["description"],
            trigger_condition=existing["trigger_condition"],
            steps=new_steps,
            prerequisites=existing["prerequisites"],
            namespace=namespace,
            reason_for_change=f"Edited via instruction: {instruction}",
        )
        return {
            "status": "edited",
            "pillar": "procedural",
            "procedure_id": proc_id,
            "name": name,
            "updated_steps": new_steps,
        }

    elif pillar == "entity":
        # Handle entity modification
        try:
            target_uuid = UUID(target_id_or_name)
            is_uuid = True
        except ValueError:
            is_uuid = False

        if is_uuid:
            async with pool.acquire() as c:
                await c.execute(
                    "UPDATE entity_edges SET fact_summary = fact_summary || ' [Edited: ' || $1 || ']' WHERE edge_id = $2 AND namespace = $3",
                    instruction,
                    target_uuid,
                    namespace,
                )
        else:
            async with pool.acquire() as c:
                await c.execute(
                    "UPDATE entity_nodes SET summary = summary || ' [Edited: ' || $1 || ']' WHERE name = $2 AND namespace = $3",
                    instruction,
                    target_id_or_name,
                    namespace,
                )
        return {"status": "edited", "pillar": "entity", "target": target_id_or_name}

    return {"status": "error", "message": f"Unsupported pillar: {pillar}"}


async def svc_memory_feedback(
    memory_ids_used: Optional[List[str]] = None,
    procedure_name: Optional[str] = None,
    success: bool = True,
    failure_reason: Optional[str] = None,
    namespace: str = "default",
) -> Dict[str, Any]:
    """Updates utility scores on used memories, and auto-patches procedures on failure."""
    memory_ids_used = memory_ids_used or []
    delta = 1 if success else -2

    # 1. Update utility scores
    updated_score_count = 0
    if memory_ids_used:
        updated_score_count = await update_utility_scores(memory_ids_used, delta=delta)

    # 2. Update procedure if provided
    proc_updated = False
    patched_steps = None

    if procedure_name:
        pool = await get_db_pool()
        if not success and failure_reason and settings.memory_llm_enabled:
            # Query current steps
            async with pool.acquire() as c:
                existing = await c.fetchrow(
                    "SELECT steps FROM procedural_memories WHERE namespace = $1 AND name = $2",
                    namespace,
                    procedure_name,
                )
            if existing:
                cur_steps = existing["steps"] if isinstance(existing["steps"], list) else []
                patched_steps = await patch_procedure_with_llm(
                    name=procedure_name,
                    current_steps=cur_steps,
                    failure_reason=failure_reason,
                )

        proc_updated = await record_procedure_feedback(
            namespace=namespace,
            name=procedure_name,
            success=success,
            patched_steps=patched_steps,
            failure_reason=failure_reason,
        )

    return {
        "status": "feedback_recorded",
        "success": success,
        "memories_updated_count": updated_score_count,
        "procedure_updated": proc_updated,
        "patched_steps": patched_steps,
    }


async def svc_memory_delete(
    target_id: str,
    pillar: Literal["semantic", "episodic", "procedural", "entity"] = "semantic",
    hard_delete: bool = False,
    namespace: str = "default",
) -> Dict[str, Any]:
    """Soft-invalidates or permanently deletes a memory record."""
    if pillar == "semantic":
        res = await delete_semantic(target_id, namespace=namespace, hard_delete=hard_delete)
    elif pillar == "episodic":
        res = await delete_episodic(target_id, namespace=namespace, hard_delete=hard_delete)
    elif pillar == "procedural":
        res = await delete_procedure(target_id, namespace=namespace, hard_delete=hard_delete)
    elif pillar == "entity":
        res = await delete_entity(target_id, namespace=namespace, hard_delete=hard_delete)
    else:
        raise ValueError(f"Unknown pillar: {pillar}")

    return {
        "status": "deleted" if res else "not_found",
        "pillar": pillar,
        "target_id": target_id,
        "hard_delete": hard_delete,
    }
