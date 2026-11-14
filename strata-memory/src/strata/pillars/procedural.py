from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
import asyncpg
from strata.db import get_db_pool
from strata.embedder import LocalEmbedder
from strata.models import ProceduralMemoryItem


async def upsert_procedure(
    name: str,
    description: str,
    trigger_condition: str,
    steps: List[str],
    prerequisites: Optional[Dict[str, Any]] = None,
    namespace: str = "default",
    reason_for_change: Optional[str] = None,
    embedding: Optional[List[float]] = None,
    conn: Optional[asyncpg.Connection] = None,
) -> str:
    """Inserts or updates a versioned procedure/skill in procedural_memories."""
    prerequisites = prerequisites or {}
    embedder = LocalEmbedder.get_instance()

    if embedding is None:
        embed_input = f"{name}: {trigger_condition} - {description}"
        embedding = embedder.embed_one(embed_input)
    vec_str = embedder.to_pgvector_str(embedding)

    pool = await get_db_pool() if conn is None else None

    async def _execute(c: asyncpg.Connection) -> str:
        # Check existing procedure
        existing = await c.fetchrow(
            """
            SELECT procedure_id, version, changelog
            FROM procedural_memories
            WHERE namespace = $1 AND name = $2;
            """,
            namespace,
            name,
        )

        now_iso = datetime.now(timezone.utc).isoformat()

        if existing:
            proc_id = str(existing["procedure_id"])
            current_version = existing["version"]
            new_version = current_version + 1
            existing_changelog = existing["changelog"] or []
            if not isinstance(existing_changelog, list):
                existing_changelog = []

            new_changelog = existing_changelog + [{
                "version": new_version,
                "timestamp": now_iso,
                "reason": reason_for_change or f"Updated to version {new_version}",
            }]

            update_sql = """
                UPDATE procedural_memories
                SET description = $1,
                    trigger_condition = $2,
                    trigger_embedding = $3::vector(768),
                    steps = $4,
                    prerequisites = $5,
                    version = $6,
                    changelog = $7,
                    is_active = TRUE,
                    updated_at = NOW()
                WHERE procedure_id = $8;
            """
            await c.execute(
                update_sql,
                description,
                trigger_condition,
                vec_str,
                steps,
                prerequisites,
                new_version,
                new_changelog,
                UUID(proc_id),
            )
            return proc_id
        else:
            initial_changelog = [{
                "version": 1,
                "timestamp": now_iso,
                "reason": reason_for_change or "Initial procedure creation",
            }]
            insert_sql = """
                INSERT INTO procedural_memories (
                    namespace, name, description, trigger_condition, trigger_embedding,
                    steps, prerequisites, version, changelog, success_count, fail_count,
                    is_active, updated_at
                )
                VALUES ($1, $2, $3, $4, $5::vector(768), $6, $7, 1, $8, 0, 0, TRUE, NOW())
                RETURNING procedure_id;
            """
            row = await c.fetchrow(
                insert_sql,
                namespace,
                name,
                description,
                trigger_condition,
                vec_str,
                steps,
                prerequisites,
                initial_changelog,
            )
            return str(row["procedure_id"])

    if conn is not None:
        return await _execute(conn)
    else:
        assert pool is not None
        async with pool.acquire() as c:
            async with c.transaction():
                return await _execute(c)


async def search_procedures(
    query_embedding: List[float],
    namespace: str = "default",
    top_k: int = 5,
    conn: Optional[asyncpg.Connection] = None,
) -> List[ProceduralMemoryItem]:
    """Ranks active procedures using composite Bayesian formula:
    Score = 0.75 * (1 - CosineDistance) + 0.25 * ((success_count + 1) / (success_count + fail_count + 2))"""
    vec_str = LocalEmbedder.to_pgvector_str(query_embedding)
    pool = await get_db_pool() if conn is None else None

    async def _execute(c: asyncpg.Connection) -> List[ProceduralMemoryItem]:
        sql = """
            SELECT
                procedure_id,
                name,
                description,
                trigger_condition,
                steps,
                prerequisites,
                version,
                success_count,
                fail_count,
                (
                    0.75 * (1.0 - (trigger_embedding <=> $1::vector(768))) +
                    0.25 * ((success_count + 1)::float / (success_count + fail_count + 2)::float)
                ) AS composite_score,
                ((success_count + 1)::float / (success_count + fail_count + 2)::float) AS success_rate
            FROM procedural_memories
            WHERE namespace = $2
              AND is_active = TRUE
            ORDER BY composite_score DESC
            LIMIT $3;
        """
        rows = await c.fetch(sql, vec_str, namespace, top_k)
        results = []
        for r in rows:
            results.append(
                ProceduralMemoryItem(
                    procedure_id=str(r["procedure_id"]),
                    name=r["name"],
                    description=r["description"],
                    trigger_condition=r["trigger_condition"],
                    steps=r["steps"] if isinstance(r["steps"], list) else [],
                    prerequisites=r["prerequisites"] if isinstance(r["prerequisites"], dict) else {},
                    version=r["version"],
                    success_count=r["success_count"],
                    fail_count=r["fail_count"],
                    success_rate=float(r["success_rate"]),
                    composite_score=float(r["composite_score"]),
                )
            )
        return results

    if conn is not None:
        return await _execute(conn)
    else:
        assert pool is not None
        async with pool.acquire() as c:
            return await _execute(c)


async def record_procedure_feedback(
    namespace: str,
    name: str,
    success: bool,
    patched_steps: Optional[List[str]] = None,
    failure_reason: Optional[str] = None,
    conn: Optional[asyncpg.Connection] = None,
) -> bool:
    """Updates procedure success/fail counts, and increments version with patched steps if provided."""
    pool = await get_db_pool() if conn is None else None

    async def _execute(c: asyncpg.Connection) -> bool:
        existing = await c.fetchrow(
            """
            SELECT procedure_id, version, changelog, steps
            FROM procedural_memories
            WHERE namespace = $1 AND name = $2;
            """,
            namespace,
            name,
        )
        if not existing:
            return False

        proc_id = existing["procedure_id"]
        now_iso = datetime.now(timezone.utc).isoformat()

        if success:
            await c.execute(
                """
                UPDATE procedural_memories
                SET success_count = success_count + 1, updated_at = NOW()
                WHERE procedure_id = $1;
                """,
                proc_id,
            )
            return True
        else:
            if patched_steps:
                cur_v = existing["version"]
                new_v = cur_v + 1
                cur_changelog = existing["changelog"] or []
                if not isinstance(cur_changelog, list):
                    cur_changelog = []

                reason = f"Auto-patched after failure: {failure_reason or 'unspecified failure'}"
                new_changelog = cur_changelog + [{
                    "version": new_v,
                    "timestamp": now_iso,
                    "reason": reason,
                }]

                await c.execute(
                    """
                    UPDATE procedural_memories
                    SET fail_count = fail_count + 1,
                        version = $1,
                        steps = $2,
                        changelog = $3,
                        updated_at = NOW()
                    WHERE procedure_id = $4;
                    """,
                    new_v,
                    patched_steps,
                    new_changelog,
                    proc_id,
                )
            else:
                await c.execute(
                    """
                    UPDATE procedural_memories
                    SET fail_count = fail_count + 1, updated_at = NOW()
                    WHERE procedure_id = $1;
                    """,
                    proc_id,
                )
            return True

    if conn is not None:
        return await _execute(conn)
    else:
        assert pool is not None
        async with pool.acquire() as c:
            async with c.transaction():
                return await _execute(c)


async def delete_procedure(
    target_id_or_name: str,
    namespace: str = "default",
    hard_delete: bool = False,
    conn: Optional[asyncpg.Connection] = None,
) -> bool:
    """Soft or hard deletes a procedure by UUID or name."""
    pool = await get_db_pool() if conn is None else None

    # Determine if target is a UUID or name
    is_uuid = False
    try:
        target_uuid = UUID(target_id_or_name)
        is_uuid = True
    except ValueError:
        target_uuid = None

    async def _execute(c: asyncpg.Connection) -> bool:
        if hard_delete:
            if is_uuid:
                res = await c.execute(
                    "DELETE FROM procedural_memories WHERE procedure_id = $1 AND namespace = $2",
                    target_uuid,
                    namespace,
                )
            else:
                res = await c.execute(
                    "DELETE FROM procedural_memories WHERE name = $1 AND namespace = $2",
                    target_id_or_name,
                    namespace,
                )
        else:
            if is_uuid:
                res = await c.execute(
                    "UPDATE procedural_memories SET is_active = FALSE WHERE procedure_id = $1 AND namespace = $2",
                    target_uuid,
                    namespace,
                )
            else:
                res = await c.execute(
                    "UPDATE procedural_memories SET is_active = FALSE WHERE name = $1 AND namespace = $2",
                    target_id_or_name,
                    namespace,
                )
        return " 0" not in res

    if conn is not None:
        return await _execute(conn)
    else:
        assert pool is not None
        async with pool.acquire() as c:
            return await _execute(c)
