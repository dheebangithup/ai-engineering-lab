from typing import Any, Dict, List, Optional
from uuid import UUID
import asyncpg
from strata.config import settings
from strata.db import get_db_pool
from strata.embedder import LocalEmbedder
from strata.models import EntityGraphItem


async def upsert_entity_node(
    name: str,
    entity_type: str,
    summary: str,
    attributes: Optional[Dict[str, Any]] = None,
    namespace: str = "default",
    embedding: Optional[List[float]] = None,
    conn: Optional[asyncpg.Connection] = None,
) -> str:
    """Upserts an entity node in entity_nodes."""
    attributes = attributes or {}
    embedder = LocalEmbedder.get_instance()
    if embedding is None:
        embed_input = f"{name} ({entity_type}): {summary}"
        embedding = await embedder.embed_one(embed_input)
    vec_str = embedder.to_pgvector_str(embedding)

    pool = await get_db_pool() if conn is None else None

    async def _execute(c: asyncpg.Connection) -> str:
        sql = """
            INSERT INTO entity_nodes (
                namespace, name, entity_type, summary, attributes, embedding, is_active, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6::vector(768), TRUE, NOW())
            ON CONFLICT (namespace, name, entity_type)
            DO UPDATE SET
                summary = EXCLUDED.summary,
                attributes = entity_nodes.attributes || EXCLUDED.attributes,
                embedding = EXCLUDED.embedding,
                is_active = TRUE,
                updated_at = NOW()
            RETURNING entity_id;
        """
        row = await c.fetchrow(sql, namespace, name, entity_type, summary, attributes, vec_str)
        return str(row["entity_id"])

    if conn is not None:
        return await _execute(conn)
    else:
        assert pool is not None
        async with pool.acquire() as c:
            return await _execute(c)


async def upsert_entity_link(
    source_name: str,
    source_type: str,
    source_summary: str,
    relation_type: str,
    target_name: str,
    target_type: str,
    target_summary: str,
    fact_summary: str,
    properties: Optional[Dict[str, Any]] = None,
    invalidate_conflicting_relations: bool = True,
    namespace: str = "default",
    conn: Optional[asyncpg.Connection] = None,
) -> str:
    """Upserts source and target nodes, optionally invalidates prior conflicting relations,
    and inserts the new active bi-temporal edge."""
    properties = properties or {}
    pool = await get_db_pool() if conn is None else None

    async def _execute(c: asyncpg.Connection) -> str:
        src_id = await upsert_entity_node(
            name=source_name,
            entity_type=source_type,
            summary=source_summary,
            namespace=namespace,
            conn=c,
        )
        tgt_id = await upsert_entity_node(
            name=target_name,
            entity_type=target_type,
            summary=target_summary,
            namespace=namespace,
            conn=c,
        )

        if invalidate_conflicting_relations:
            # Invalidate any prior active edge with the same source and relation type
            invalidate_sql = """
                UPDATE entity_edges
                SET valid_until = NOW()
                WHERE namespace = $1
                  AND source_entity_id = $2
                  AND relation_type = $3
                  AND (valid_until IS NULL OR valid_until > NOW());
            """
            await c.execute(invalidate_sql, namespace, UUID(src_id), relation_type)

        insert_edge_sql = """
            INSERT INTO entity_edges (
                namespace, source_entity_id, relation_type, target_entity_id,
                fact_summary, properties, valid_from
            )
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            RETURNING edge_id;
        """
        edge_row = await c.fetchrow(
            insert_edge_sql,
            namespace,
            UUID(src_id),
            relation_type,
            UUID(tgt_id),
            fact_summary,
            properties,
        )
        return str(edge_row["edge_id"])

    if conn is not None:
        return await _execute(conn)
    else:
        assert pool is not None
        async with pool.acquire() as c:
            async with c.transaction():
                return await _execute(c)


async def search_entity_subgraph(
    query_embedding: List[float],
    query_text: str,
    namespace: str = "default",
    top_k: int = 5,
    similarity_threshold: Optional[float] = None,
    conn: Optional[asyncpg.Connection] = None,
) -> List[EntityGraphItem]:
    """Finds top matching entity_nodes via vector or ILIKE match, then performs
    a 1-hop traversal across active entity_edges."""
    vec_str = LocalEmbedder.to_pgvector_str(query_embedding)
    clean_query = query_text.strip()
    thresh = (
        similarity_threshold
        if similarity_threshold is not None
        else settings.entity_similarity_threshold
    )
    pool = await get_db_pool() if conn is None else None

    async def _execute(c: asyncpg.Connection) -> List[EntityGraphItem]:
        sql = """
            WITH seed_nodes AS (
                SELECT entity_id
                FROM entity_nodes
                WHERE namespace = $1
                  AND is_active = TRUE
                  AND (
                      ($2 <> '' AND name ILIKE '%' || $2 || '%')
                      OR (1.0 - (embedding <=> $3::vector(768))) >= $5
                  )
                ORDER BY (embedding <=> $3::vector(768)) ASC
                LIMIT $4
            )
            SELECT
                e.edge_id,
                src.name AS source_name,
                src.entity_type AS source_type,
                e.relation_type,
                tgt.name AS target_name,
                tgt.entity_type AS target_type,
                e.fact_summary,
                e.properties,
                e.valid_from
            FROM entity_edges e
            JOIN entity_nodes src ON e.source_entity_id = src.entity_id
            JOIN entity_nodes tgt ON e.target_entity_id = tgt.entity_id
            WHERE e.namespace = $1
              AND (e.valid_until IS NULL OR e.valid_until > NOW())
              AND src.is_active = TRUE
              AND tgt.is_active = TRUE
              AND (
                  e.source_entity_id IN (SELECT entity_id FROM seed_nodes)
                  OR e.target_entity_id IN (SELECT entity_id FROM seed_nodes)
              )
            ORDER BY e.valid_from DESC
            LIMIT $4 * 3;
        """
        rows = await c.fetch(sql, namespace, clean_query, vec_str, top_k, thresh)
        results = []
        for r in rows:
            results.append(
                EntityGraphItem(
                    edge_id=str(r["edge_id"]),
                    source_name=r["source_name"],
                    source_type=r["source_type"],
                    relation_type=r["relation_type"],
                    target_name=r["target_name"],
                    target_type=r["target_type"],
                    fact_summary=r["fact_summary"],
                    properties=r["properties"] if isinstance(r["properties"], dict) else {},
                    valid_from=r["valid_from"],
                )
            )
        return results

    if conn is not None:
        return await _execute(conn)
    else:
        assert pool is not None
        async with pool.acquire() as c:
            return await _execute(c)


async def delete_entity(
    target_id_or_name: str,
    namespace: str = "default",
    hard_delete: bool = False,
    conn: Optional[asyncpg.Connection] = None,
) -> bool:
    """Soft or hard deletes an entity edge or entity node."""
    pool = await get_db_pool() if conn is None else None

    # Check if target is UUID
    try:
        target_uuid = UUID(target_id_or_name)
    except ValueError:
        target_uuid = None

    async def _execute(c: asyncpg.Connection) -> bool:
        if target_uuid:
            # Try edge first
            if hard_delete:
                res = await c.execute(
                    "DELETE FROM entity_edges WHERE edge_id = $1 AND namespace = $2",
                    target_uuid,
                    namespace,
                )
                if " 0" not in res:
                    return True
                # If not edge, try node
                res_node = await c.execute(
                    "DELETE FROM entity_nodes WHERE entity_id = $1 AND namespace = $2",
                    target_uuid,
                    namespace,
                )
                return " 0" not in res_node
            else:
                # Soft delete edge
                res = await c.execute(
                    "UPDATE entity_edges SET valid_until = NOW() WHERE edge_id = $1 AND namespace = $2 AND (valid_until IS NULL OR valid_until > NOW())",
                    target_uuid,
                    namespace,
                )
                if " 0" not in res:
                    return True
                # If not edge, soft-delete node and all attached edges
                res_node = await c.execute(
                    "UPDATE entity_nodes SET is_active = FALSE WHERE entity_id = $1 AND namespace = $2 AND is_active = TRUE",
                    target_uuid,
                    namespace,
                )
                if " 0" not in res_node:
                    await c.execute(
                        """
                        UPDATE entity_edges
                        SET valid_until = NOW()
                        WHERE namespace = $1
                          AND (valid_until IS NULL OR valid_until > NOW())
                          AND (source_entity_id = $2 OR target_entity_id = $2);
                        """,
                        namespace,
                        target_uuid,
                    )
                    return True
                return False
        else:
            # Delete node by name
            if hard_delete:
                res = await c.execute(
                    "DELETE FROM entity_nodes WHERE name = $1 AND namespace = $2",
                    target_id_or_name,
                    namespace,
                )
                return " 0" not in res
            else:
                res_node = await c.execute(
                    "UPDATE entity_nodes SET is_active = FALSE WHERE name = $1 AND namespace = $2 AND is_active = TRUE",
                    target_id_or_name,
                    namespace,
                )
                # Soft delete all active edges attached to this node
                res_edge = await c.execute(
                    """
                    UPDATE entity_edges
                    SET valid_until = NOW()
                    WHERE namespace = $1
                      AND (valid_until IS NULL OR valid_until > NOW())
                      AND (
                          source_entity_id IN (SELECT entity_id FROM entity_nodes WHERE name = $2 AND namespace = $1)
                          OR target_entity_id IN (SELECT entity_id FROM entity_nodes WHERE name = $2 AND namespace = $1)
                      );
                    """,
                    namespace,
                    target_id_or_name,
                )
                return (" 0" not in res_node) or (" 0" not in res_edge)

    if conn is not None:
        return await _execute(conn)
    else:
        assert pool is not None
        async with pool.acquire() as c:
            return await _execute(c)
