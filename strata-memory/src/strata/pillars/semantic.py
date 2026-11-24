from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
import asyncpg
from strata.config import settings
from strata.db import get_db_pool
from strata.embedder import LocalEmbedder


async def add_or_supersede_semantic(
    summary: str,
    namespace: str = "default",
    payload: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
    confidence: float = 1.0,
    source_id: Optional[str] = None,
    supersede_memory_id: Optional[str] = None,
    embedding: Optional[List[float]] = None,
    contradiction_threshold: Optional[float] = None,
    ttl_seconds: Optional[int] = None,
    conn: Optional[asyncpg.Connection] = None,
) -> Tuple[str, Optional[str]]:
    """Inserts a semantic memory. If supersede_memory_id is provided or an existing active memory
    in the same namespace has cosine similarity > contradiction_threshold, invalidates the old memory.
    Supports optional ttl_seconds for time-bounded validity."""
    payload = payload or {}
    tags = tags or []
    embedder = LocalEmbedder.get_instance()
    threshold = (
        contradiction_threshold
        if contradiction_threshold is not None
        else settings.contradiction_threshold
    )

    if embedding is None:
        embedding = await embedder.embed_one(summary)
    vec_str = embedder.to_pgvector_str(embedding)

    pool = await get_db_pool() if conn is None else None

    async def _execute(c: asyncpg.Connection) -> Tuple[str, Optional[str]]:
        nonlocal supersede_memory_id

        # Auto-detect near-duplicate or contradictory memory if not explicitly provided
        if supersede_memory_id is None:
            check_sql = """
                SELECT memory_id, (1.0 - (embedding <=> $2::vector(768))) AS sim
                FROM memories
                WHERE namespace = $1
                  AND type = 'semantic'
                  AND (valid_until IS NULL OR valid_until > NOW())
                  AND (1.0 - (embedding <=> $2::vector(768))) > $3
                ORDER BY (embedding <=> $2::vector(768)) ASC
                LIMIT 1;
            """
            row = await c.fetchrow(check_sql, namespace, vec_str, threshold)
            if row:
                sim = float(row["sim"])
                summary_lower = summary.lower()
                is_update_intent = any(
                    k in summary_lower for k in ["update", "changed", "instead of", "no longer", "replaced", "supersede"]
                )
                # Fact Reaffirmation (Agent Memory Architect): If identical/near-identical fact (sim >= 0.96) without update intent
                # Reaffirm the existing fact by bumping access_count and resetting reaffirmed_at = NOW() (half-life decay reset)
                if sim >= 0.96 and not is_update_intent:
                    existing_id = str(row["memory_id"])
                    await c.execute(
                        """
                        UPDATE memories
                        SET reaffirmed_at = NOW(), access_count = access_count + 1
                        WHERE memory_id = $1;
                        """,
                        row["memory_id"],
                    )
                    return existing_id, None

                supersede_memory_id = str(row["memory_id"])

        insert_sql = """
            INSERT INTO memories (
                namespace, type, summary, payload, tags, embedding,
                confidence, utility_score, access_count, source_id, valid_from, valid_until
            )
            VALUES (
                $1, 'semantic', $2, $3, $4, $5::vector(768), $6, 0, 0, $7, NOW(),
                CASE WHEN $8::int IS NOT NULL THEN NOW() + ($8::int || ' seconds')::INTERVAL ELSE NULL END
            )
            RETURNING memory_id;
        """
        new_row = await c.fetchrow(
            insert_sql,
            namespace,
            summary,
            payload,
            tags,
            vec_str,
            confidence,
            source_id,
            ttl_seconds,
        )
        new_id = str(new_row["memory_id"])

        if supersede_memory_id:
            try:
                sup_uuid = UUID(supersede_memory_id)
                update_sql = """
                    UPDATE memories
                    SET valid_until = NOW(), superseded_by = $1
                    WHERE memory_id = $2
                      AND namespace = $3
                      AND (valid_until IS NULL OR valid_until > NOW());
                """
                await c.execute(update_sql, UUID(new_id), sup_uuid, namespace)
            except ValueError:
                # If invalid UUID string, ignore superseding
                supersede_memory_id = None

        return new_id, supersede_memory_id

    if conn is not None:
        return await _execute(conn)
    else:
        assert pool is not None
        async with pool.acquire() as c:
            async with c.transaction():
                return await _execute(c)


async def delete_semantic(
    memory_id: str,
    namespace: str = "default",
    hard_delete: bool = False,
    conn: Optional[asyncpg.Connection] = None,
) -> bool:
    """Soft or hard deletes a semantic memory."""
    try:
        mem_uuid = UUID(memory_id)
    except ValueError:
        return False

    pool = await get_db_pool() if conn is None else None

    async def _execute(c: asyncpg.Connection) -> bool:
        if hard_delete:
            res = await c.execute(
                "DELETE FROM memories WHERE memory_id = $1 AND namespace = $2 AND type = 'semantic'",
                mem_uuid,
                namespace,
            )
        else:
            res = await c.execute(
                "UPDATE memories SET valid_until = NOW() WHERE memory_id = $1 AND namespace = $2 AND type = 'semantic' AND (valid_until IS NULL OR valid_until > NOW())",
                mem_uuid,
                namespace,
            )
        return " 0" not in res

    if conn is not None:
        return await _execute(conn)
    else:
        assert pool is not None
        async with pool.acquire() as c:
            return await _execute(c)
