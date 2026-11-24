import json
import logging
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from strata.config import settings
from strata.db import get_db_pool
from strata.llm_processor.prompts import EDIT_INSTRUCTION_PROMPT
from strata.llm_processor.router import (
    distill_episodes_with_llm,
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
    PruneRequest,
    PruneResponse,
    PurgeNamespaceRequest,
    PurgeNamespaceResponse,
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
from strata.working_memory import working_memory

logger = logging.getLogger("strata.service")


async def svc_memory_ingest(
    raw_text: str,
    namespace: str = "default",
    fast_mode: bool = False,
    source_id: Optional[str] = None,
    contradiction_threshold: Optional[float] = None,
    use_decision_model: Optional[bool] = None,
    ttl_seconds: Optional[int] = None,
    laya_mode: Optional[str] = None,
) -> IngestResponse:
    """Autonomous 4-pillar extraction & storage using Laya Decision Engine and Small LLM."""
    return await process_and_ingest(
        raw_text=raw_text,
        namespace=namespace,
        fast_mode=fast_mode,
        source_id=source_id,
        contradiction_threshold=contradiction_threshold,
        use_decision_model=use_decision_model,
        ttl_seconds=ttl_seconds,
        laya_mode=laya_mode,
    )


async def svc_memory_recall(
    query: str,
    namespace: str = "default",
    pillars: Optional[List[str]] = None,
    top_k: int = 5,
    token_budget: int = 1500,
    match_threshold: Optional[float] = None,
    min_score: Optional[float] = None,
    similarity_threshold: Optional[float] = None,
) -> RecallResponse:
    """Zero-LLM deterministic hybrid RRF + graph + procedural retrieval.
    If pillars is None, Laya dynamically selects the relevant pillars based on query intent."""
    req = RecallRequest(
        query=query,
        namespace=namespace,
        pillars=pillars,
        top_k=top_k,
        token_budget=token_budget,
        match_threshold=match_threshold,
        min_score=min_score,
        similarity_threshold=similarity_threshold,
    )
    return await memory_recall_internal(req)


async def svc_memory_store_explicit(
    pillar: Literal["semantic", "episodic", "procedural", "entity"],
    payload: Dict[str, Any],
    namespace: str = "default",
    ttl_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    """Direct, zero-LLM structured write to any of the 4 pillars with optional TTL."""
    effective_ttl = ttl_seconds if ttl_seconds is not None else payload.get("ttl_seconds")

    if pillar == "semantic":
        mem_id, superseded_id = await add_or_supersede_semantic(
            summary=payload.get("summary", ""),
            namespace=namespace,
            payload=payload.get("payload", {}),
            tags=payload.get("tags", []),
            confidence=float(payload.get("confidence", 1.0)),
            source_id=payload.get("source_id"),
            supersede_memory_id=payload.get("supersede_memory_id"),
            ttl_seconds=effective_ttl,
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
            ttl_seconds=effective_ttl,
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


async def svc_memory_prune(
    namespace: str = "default",
    distill_episodes: bool = True,
    episodic_older_than_days: Optional[int] = 30,
    superseded_older_than_days: int = 90,
    retire_toxic_threshold: Optional[int] = -5,
    batch_size: int = 20,
) -> PruneResponse:
    """Safely consolidates and prunes stale memories:
    1. Retires toxic memories (utility_score <= threshold) by soft-invalidating them.
    2. Gathers soft-expired or old episodic memories, invokes Cognitive Distillation
       via Small LLM to synthesize durable runbooks or semantic facts, then purges the raw episodes.
    3. Physically purges superseded/soft-deleted rows older than superseded_older_than_days."""
    pool = await get_db_pool()

    toxic_retired = 0
    distilled_facts_count = 0
    distilled_procedures_count = 0
    episodes_pruned_count = 0
    superseded_pruned_count = 0
    distillation_summary = ""

    async with pool.acquire() as conn:
        # Step 1: Auto-retire toxic memories
        if retire_toxic_threshold is not None:
            res_toxic = await conn.execute(
                """
                UPDATE memories
                SET valid_until = NOW()
                WHERE namespace = $1
                  AND utility_score <= $2
                  AND (valid_until IS NULL OR valid_until > NOW());
                """,
                namespace,
                retire_toxic_threshold,
            )
            try:
                toxic_retired = int(res_toxic.split(" ")[1])
            except (IndexError, ValueError):
                toxic_retired = 0

        # Step 2: Cognitive Distillation of Expiring Episodes
        fetch_episodes_sql = """
            SELECT memory_id, summary, payload, tags, utility_score, created_at
            FROM memories
            WHERE namespace = $1
              AND type = 'episodic'
              AND (
                  (valid_until IS NOT NULL AND valid_until <= NOW())
                  OR ($2::int IS NOT NULL AND created_at < NOW() - ($2::int || ' days')::INTERVAL)
              )
            ORDER BY created_at ASC
            LIMIT $3;
        """
        exp_rows = await conn.fetch(fetch_episodes_sql, namespace, episodic_older_than_days, batch_size)

        if exp_rows:
            ep_ids = [r["memory_id"] for r in exp_rows]
            ep_contexts = []
            for r in exp_rows:
                pl = r["payload"] if isinstance(r["payload"], dict) else {}
                ep_contexts.append({
                    "id": str(r["memory_id"]),
                    "summary": r["summary"],
                    "situation": pl.get("situation", ""),
                    "action_taken": pl.get("action_taken", ""),
                    "outcome": pl.get("outcome", ""),
                    "success": pl.get("success", True),
                    "tags": r["tags"],
                })

            if distill_episodes:
                distillation_plan = await distill_episodes_with_llm(ep_contexts)
                distillation_summary = distillation_plan.reasoning

                if distillation_plan.has_durable_knowledge:
                    # Ingest distilled semantic facts
                    for fact in distillation_plan.semantic_facts:
                        await add_or_supersede_semantic(
                            summary=fact.summary,
                            namespace=namespace,
                            tags=list(set(fact.tags + ["distilled_from_episodic"])),
                            confidence=fact.confidence,
                            source_id="cognitive_distillation",
                            conn=conn,
                        )
                        distilled_facts_count += 1

                    # Ingest or evolve procedural runbooks
                    for proc in distillation_plan.procedures:
                        await upsert_procedure(
                            name=proc.name,
                            description=proc.description,
                            trigger_condition=proc.trigger_condition,
                            steps=proc.steps,
                            namespace=namespace,
                            reason_for_change="Synthesized from episodic experiences via Cognitive Distillation",
                            conn=conn,
                        )
                        distilled_procedures_count += 1

            # Once distilled (or if distillation bypassed), safely delete these raw episodic rows
            del_ep_res = await conn.execute(
                "DELETE FROM memories WHERE memory_id = ANY($1::uuid[]) AND namespace = $2",
                ep_ids,
                namespace,
            )
            try:
                episodes_pruned_count = int(del_ep_res.split(" ")[1])
            except (IndexError, ValueError):
                episodes_pruned_count = len(ep_ids)

        # Step 3: Physically purge superseded/soft-deleted rows older than retention threshold
        del_sup_mem = await conn.execute(
            """
            DELETE FROM memories
            WHERE namespace = $1
              AND valid_until IS NOT NULL
              AND valid_until < NOW() - ($2::int || ' days')::INTERVAL;
            """,
            namespace,
            superseded_older_than_days,
        )
        try:
            mem_purged = int(del_sup_mem.split(" ")[1])
        except (IndexError, ValueError):
            mem_purged = 0

        del_sup_edges = await conn.execute(
            """
            DELETE FROM entity_edges
            WHERE namespace = $1
              AND valid_until IS NOT NULL
              AND valid_until < NOW() - ($2::int || ' days')::INTERVAL;
            """,
            namespace,
            superseded_older_than_days,
        )
        try:
            edge_purged = int(del_sup_edges.split(" ")[1])
        except (IndexError, ValueError):
            edge_purged = 0

        superseded_pruned_count = mem_purged + edge_purged

    return PruneResponse(
        namespace=namespace,
        distilled_facts_created=distilled_facts_count,
        distilled_procedures_created=distilled_procedures_count,
        episodes_pruned=episodes_pruned_count,
        superseded_pruned=superseded_pruned_count,
        toxic_memories_retired=toxic_retired,
        details={
            "distillation_summary": distillation_summary,
            "superseded_memories_purged": mem_purged,
            "superseded_edges_purged": edge_purged,
        },
    )


async def svc_memory_purge_namespace(
    namespace: str,
    confirm: bool = False,
) -> PurgeNamespaceResponse:
    """Completely purges all data within a specified namespace (GDPR / reset compliance)."""
    if not confirm:
        return PurgeNamespaceResponse(
            namespace=namespace,
            purged=False,
            deleted_counts={"error": "confirm must be set to True to execute namespace purge"},
        )

    pool = await get_db_pool()
    counts = {}
    async with pool.acquire() as conn:
        async with conn.transaction():
            res_mem = await conn.execute("DELETE FROM memories WHERE namespace = $1", namespace)
            counts["memories"] = int(res_mem.split(" ")[1]) if " " in res_mem else 0

            res_proc = await conn.execute("DELETE FROM procedural_memories WHERE namespace = $1", namespace)
            counts["procedural"] = int(res_proc.split(" ")[1]) if " " in res_proc else 0

            res_edges = await conn.execute("DELETE FROM entity_edges WHERE namespace = $1", namespace)
            counts["entity_edges"] = int(res_edges.split(" ")[1]) if " " in res_edges else 0

            res_nodes = await conn.execute("DELETE FROM entity_nodes WHERE namespace = $1", namespace)
            counts["entity_nodes"] = int(res_nodes.split(" ")[1]) if " " in res_nodes else 0

    return PurgeNamespaceResponse(
        namespace=namespace,
        purged=True,
        deleted_counts=counts,
    )


# ============================================================================
# WORKING MEMORY (SHORT-TERM CONTEXT & TOOL OUTPUT PINNING)
# ============================================================================

def svc_working_memory_add(
    namespace: str,
    session_id: str,
    role: str,
    content: str,
    turn_id: Optional[int] = None,
    tool_call_id: Optional[str] = None,
    tool_name: Optional[str] = None,
    is_tool_output: bool = False,
    protected: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Adds a message to the active working memory buffer."""
    item = working_memory.add_message(
        namespace=namespace,
        session_id=session_id,
        role=role,
        content=content,
        turn_id=turn_id,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        is_tool_output=is_tool_output,
        protected=protected,
        metadata=metadata,
    )
    return {
        "item_id": item.item_id,
        "session_id": item.session_id,
        "turn_id": item.turn_id,
        "role": item.role,
        "protected": item.protected,
        "token_count": item.token_count,
    }


def svc_working_memory_add_tool_output(
    namespace: str,
    session_id: str,
    tool_call_id: str,
    tool_name: str,
    content: str,
    protected: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Adds a tool execution result, pinned as protected=True by default to eliminate Eviction Policy Bug."""
    item = working_memory.add_tool_output(
        namespace=namespace,
        session_id=session_id,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        content=content,
        protected=protected,
        metadata=metadata,
    )
    return {
        "item_id": item.item_id,
        "session_id": item.session_id,
        "turn_id": item.turn_id,
        "tool_call_id": item.tool_call_id,
        "tool_name": item.tool_name,
        "protected": item.protected,
        "token_count": item.token_count,
    }


def svc_working_memory_unprotect(
    namespace: str,
    session_id: str,
    tool_call_id: str,
) -> bool:
    """Unprotects a tool result once dependent reasoning finishes, allowing eviction if needed."""
    return working_memory.unprotect_tool(namespace, session_id, tool_call_id)


def svc_working_memory_get(
    namespace: str,
    session_id: str,
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """Returns active working memory items, enforcing max_tokens budget if specified (never evicting protected items)."""
    if max_tokens is not None:
        items = working_memory.enforce_budget(namespace, session_id, max_tokens)
    else:
        items = working_memory.get_items(namespace, session_id)
    return {
        "namespace": namespace,
        "session_id": session_id,
        "item_count": len(items),
        "total_tokens": sum(i.token_count for i in items),
        "items": [
            {
                "item_id": i.item_id,
                "turn_id": i.turn_id,
                "role": i.role,
                "content": i.content,
                "tool_call_id": i.tool_call_id,
                "tool_name": i.tool_name,
                "protected": i.protected,
                "token_count": i.token_count,
            }
            for i in items
        ],
    }


def svc_working_memory_clear(namespace: str, session_id: str) -> int:
    """Clears working memory for a given session."""
    return working_memory.clear(namespace, session_id)
