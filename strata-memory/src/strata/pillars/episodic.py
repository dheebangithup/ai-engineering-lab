from typing import Any, Dict, List, Optional
from uuid import UUID
import asyncpg
from strata.db import get_db_pool
from strata.embedder import LocalEmbedder


async def record_episode(
    summary: str,
    situation: Optional[str] = None,
    action_taken: Optional[str] = None,
    outcome: Optional[str] = None,
    success: bool = True,
    namespace: str = "default",
    tags: Optional[List[str]] = None,
    extra_payload: Optional[Dict[str, Any]] = None,
    source_id: Optional[str] = None,
    embedding: Optional[List[float]] = None,
    conn: Optional[asyncpg.Connection] = None,
) -> str:
    """Records an immutable episodic trace into the memories table."""
    tags = tags or []
    payload: Dict[str, Any] = {
        "situation": situation or "",
        "action_taken": action_taken or "",
        "outcome": outcome or "",
        "success": success,
    }
    if extra_payload:
        payload.update(extra_payload)

    embedder = LocalEmbedder.get_instance()
    if embedding is None:
        # Build embedding from combined context for maximum semantic retrieval power
        embed_input = f"{summary} Situation: {situation or ''} Action: {action_taken or ''} Outcome: {outcome or ''}"
        embedding = embedder.embed_one(embed_input)
    vec_str = embedder.to_pgvector_str(embedding)

    pool = await get_db_pool() if conn is None else None

    async def _execute(c: asyncpg.Connection) -> str:
        insert_sql = """
            INSERT INTO memories (
                namespace, type, summary, payload, tags, embedding,
                confidence, utility_score, access_count, source_id, valid_from
            )
            VALUES ($1, 'episodic', $2, $3, $4, $5::vector(768), 1.0, 0, 0, $6, NOW())
            RETURNING memory_id;
        """
        row = await c.fetchrow(
            insert_sql,
            namespace,
            summary,
            payload,
            tags,
            vec_str,
            source_id,
        )
        return str(row["memory_id"])

    if conn is not None:
        return await _execute(conn)
    else:
        assert pool is not None
        async with pool.acquire() as c:
            return await _execute(c)


async def update_utility_scores(
    memory_ids: List[str],
    delta: int,
    conn: Optional[asyncpg.Connection] = None,
) -> int:
    """Updates utility_score = utility_score + delta for the provided memory IDs."""
    if not memory_ids:
        return 0

    valid_uuids: List[UUID] = []
    for mid in memory_ids:
        try:
            valid_uuids.append(UUID(mid))
        except ValueError:
            continue

    if not valid_uuids:
        return 0

    pool = await get_db_pool() if conn is None else None

    async def _execute(c: asyncpg.Connection) -> int:
        update_sql = """
            UPDATE memories
            SET utility_score = utility_score + $1
            WHERE memory_id = ANY($2::uuid[]);
        """
        res = await c.execute(update_sql, delta, valid_uuids)
        # res format is "UPDATE <count>"
        try:
            return int(res.split(" ")[1])
        except (IndexError, ValueError):
            return len(valid_uuids)

    if conn is not None:
        return await _execute(conn)
    else:
        assert pool is not None
        async with pool.acquire() as c:
            return await _execute(c)


async def delete_episodic(
    memory_id: str,
    namespace: str = "default",
    hard_delete: bool = False,
    conn: Optional[asyncpg.Connection] = None,
) -> bool:
    """Soft or hard deletes an episodic memory."""
    try:
        mem_uuid = UUID(memory_id)
    except ValueError:
        return False

    pool = await get_db_pool() if conn is None else None

    async def _execute(c: asyncpg.Connection) -> bool:
        if hard_delete:
            res = await c.execute(
                "DELETE FROM memories WHERE memory_id = $1 AND namespace = $2 AND type = 'episodic'",
                mem_uuid,
                namespace,
            )
        else:
            res = await c.execute(
                "UPDATE memories SET valid_until = NOW() WHERE memory_id = $1 AND namespace = $2 AND type = 'episodic' AND valid_until IS NULL",
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
