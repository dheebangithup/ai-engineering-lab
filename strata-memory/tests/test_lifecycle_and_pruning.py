import asyncio
import pytest
from strata.db import get_db_pool, close_db_pool, run_migrations
from strata.service import (
    svc_memory_store_explicit,
    svc_memory_recall,
    svc_memory_prune,
    svc_memory_purge_namespace,
    svc_memory_delete,
)
from strata.pillars.entity_graph import search_entity_subgraph, delete_entity


@pytest.mark.asyncio
async def test_ttl_and_temporal_recall():
    """Verify memories with TTL are active before expiration and automatically excluded after expiration."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1;")
        await run_migrations()
    except Exception as e:
        pytest.skip(f"Database not accessible ({e}), skipping live test.")

    test_ns = "test_ttl_lifecycle"
    await svc_memory_purge_namespace(namespace=test_ns, confirm=True)

    # 1. Insert permanent fact (valid_until = NULL)
    perm_res = await svc_memory_store_explicit(
        pillar="semantic",
        payload={"summary": "Postgres uses MVCC for transactions."},
        namespace=test_ns,
    )
    assert perm_res["status"] == "stored"

    # 2. Insert active TTL fact (valid for 1 hour)
    active_ttl_res = await svc_memory_store_explicit(
        pillar="semantic",
        payload={"summary": "Temporary cluster maintenance scheduled for tonight."},
        ttl_seconds=3600,
        namespace=test_ns,
    )
    assert active_ttl_res["status"] == "stored"

    # 3. Insert expiring TTL fact (valid for 1 second)
    exp_ttl_res = await svc_memory_store_explicit(
        pillar="semantic",
        payload={"summary": "Ephemeral OTP code 992819 expires immediately."},
        ttl_seconds=1,
        namespace=test_ns,
    )
    assert exp_ttl_res["status"] == "stored"

    # Immediate recall: both permanent and active TTL facts should be found
    recall_1 = await svc_memory_recall(
        query="Postgres MVCC transactions or cluster maintenance or OTP code",
        namespace=test_ns,
        top_k=10,
    )
    found_summaries = [s.summary for s in recall_1.semantic]
    assert any("Postgres" in s for s in found_summaries)
    assert any("maintenance" in s for s in found_summaries)

    # Sleep 1.5s so the 1-second TTL fact expires
    await asyncio.sleep(1.5)

    # Subsequent recall: the 1s TTL fact must be logically excluded!
    recall_2 = await svc_memory_recall(
        query="Ephemeral OTP code 992819 expires immediately",
        namespace=test_ns,
        top_k=10,
    )
    found_summaries_2 = [s.summary for s in recall_2.semantic]
    assert not any("992819" in s for s in found_summaries_2)

    # Cleanup
    await svc_memory_purge_namespace(namespace=test_ns, confirm=True)


@pytest.mark.asyncio
async def test_toxic_memory_retirement():
    """Verify memories with negative utility score (<= -5) are automatically retired by prune."""
    try:
        pool = await get_db_pool()
        await run_migrations()
    except Exception as e:
        pytest.skip(f"Database not accessible ({e}), skipping live test.")

    test_ns = "test_toxic_prune"
    await svc_memory_purge_namespace(namespace=test_ns, confirm=True)

    # 1. Store a memory and manually set utility_score = -6
    stored = await svc_memory_store_explicit(
        pillar="semantic",
        payload={"summary": "This obsolete advice caused 3 consecutive production failures."},
        namespace=test_ns,
    )
    mem_id = stored["memory_id"]

    async with pool.acquire() as conn:
        await conn.execute("UPDATE memories SET utility_score = -6 WHERE memory_id = $1", mem_id)

    # 2. Run prune
    prune_res = await svc_memory_prune(
        namespace=test_ns,
        retire_toxic_threshold=-5,
        distill_episodes=False,
    )
    assert prune_res.toxic_memories_retired >= 1

    # 3. Recall should no longer return this memory
    recall = await svc_memory_recall(
        query="obsolete advice caused production failures",
        namespace=test_ns,
    )
    assert not any("obsolete advice" in s.summary for s in recall.semantic)

    # Cleanup
    await svc_memory_purge_namespace(namespace=test_ns, confirm=True)


@pytest.mark.asyncio
async def test_entity_node_soft_delete():
    """Verify soft-deleting an entity node marks it is_active=FALSE and invalidates its edges."""
    try:
        pool = await get_db_pool()
        await run_migrations()
    except Exception as e:
        pytest.skip(f"Database not accessible ({e}), skipping live test.")

    test_ns = "test_entity_lifecycle"
    await svc_memory_purge_namespace(namespace=test_ns, confirm=True)

    # 1. Store entity link
    await svc_memory_store_explicit(
        pillar="entity",
        payload={
            "source_name": "StagingCluster",
            "source_type": "infrastructure",
            "source_summary": "Pre-production testing environment",
            "relation_type": "RUNS_IN",
            "target_name": "AWS_Region",
            "target_type": "cloud",
            "target_summary": "us-east-1",
            "fact_summary": "StagingCluster runs in AWS_Region us-east-1",
        },
        namespace=test_ns,
    )

    # Verify active in search
    recall_1 = await svc_memory_recall(query="StagingCluster AWS", namespace=test_ns, pillars=["entity"])
    assert len(recall_1.entities) > 0

    # 2. Soft-delete the entity node
    deleted = await delete_entity(target_id_or_name="StagingCluster", namespace=test_ns, hard_delete=False)
    assert deleted is True

    # 3. Search should return 0 active edges
    recall_2 = await svc_memory_recall(query="StagingCluster AWS", namespace=test_ns, pillars=["entity"])
    assert len(recall_2.entities) == 0

    # Cleanup
    await svc_memory_purge_namespace(namespace=test_ns, confirm=True)


@pytest.mark.asyncio
async def test_episodic_compaction_and_prune():
    """Verify expired episodic memories are pruned and deleted safely from PostgreSQL."""
    try:
        pool = await get_db_pool()
        await run_migrations()
    except Exception as e:
        pytest.skip(f"Database not accessible ({e}), skipping live test.")

    test_ns = "test_compaction_prune"
    await svc_memory_purge_namespace(namespace=test_ns, confirm=True)

    # 1. Store episodic memory with ttl_seconds=1
    ep_res = await svc_memory_store_explicit(
        pillar="episodic",
        payload={
            "summary": "Resolved connection timeout by increasing pool max_inactive_connection_lifetime",
            "situation": "Neon serverless dropped idle TCP connections",
            "action_taken": "Configured max_inactive_connection_lifetime=300 in db.py pool setup",
            "outcome": "Connection drops ceased completely",
            "success": True,
        },
        ttl_seconds=1,
        namespace=test_ns,
    )
    ep_id = ep_res["memory_id"]

    # Sleep so it soft-expires
    await asyncio.sleep(1.5)

    # 2. Run prune with distillation (LLM will summarize or fallback gracefully)
    prune_res = await svc_memory_prune(
        namespace=test_ns,
        distill_episodes=True,
        episodic_older_than_days=0,
    )
    assert prune_res.episodes_pruned >= 1

    # 3. Verify the episodic row is physically gone from PostgreSQL
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT memory_id FROM memories WHERE memory_id = $1", ep_id)
        assert row is None

    # Cleanup
    await svc_memory_purge_namespace(namespace=test_ns, confirm=True)
    await close_db_pool()
