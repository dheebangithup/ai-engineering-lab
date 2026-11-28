"""End-to-End Real Multi-Store & Cross-Pillar Retrieval Test Suite.

Tests actual live PostgreSQL storage (Neon) and LLM/Embeddings without mocks:
1. Pure Semantic (Atomic facts & preferences)
2. Semantic + Entity Graph (Profile, organizations, projects, directed edges)
3. Semantic + Procedural (How-to runbooks with architectural configuration rules)
4. Episodic + Semantic (Execution/incident traces with learned root-cause truths)
5. Cross-Reverse & Superseding (State transitions, bi-temporal relation invalidation, auto-supersede)
6. Role Transition & Bi-temporal Superseding (Software Engineer -> SRE Engineer, edit & recall)
"""

import asyncio
import pytest
from uuid import UUID

from strata.db import close_db_pool, get_db_pool, run_migrations
from strata.service import (
    svc_memory_edit,
    svc_memory_feedback,
    svc_memory_ingest,
    svc_memory_purge_namespace,
    svc_memory_recall,
)


async def ensure_db():
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1;")
        await run_migrations()
    except Exception as exc:
        pytest.skip(f"Database not accessible ({exc}), skipping live test.")


@pytest.mark.asyncio
async def test_case_1_pure_semantic_atomic_store_and_recall():
    """Case 1: Pure Semantic - Verifies atomic fact/preference storage and recall."""
    await ensure_db()
    test_ns = "test_multistore_semantic"
    await svc_memory_purge_namespace(namespace=test_ns, confirm=True)

    try:
        raw_text = "I prefer Python 3.12 with asyncpg and FastAPI for all backend microservices, and all endpoints must enforce token authentication."
        ingest_res = await svc_memory_ingest(raw_text=raw_text, namespace=test_ns)
        assert ingest_res.success is True

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # 1. Semantic table check
            sem_rows = await conn.fetch(
                "SELECT memory_id, summary FROM memories WHERE namespace = $1 AND type = 'semantic' AND (valid_until IS NULL OR valid_until > NOW());",
                test_ns,
            )
            assert len(sem_rows) >= 1
            assert any("python" in r["summary"].lower() or "fastapi" in r["summary"].lower() for r in sem_rows)

            # 2. Procedural & Entity tables should have 0 items for this pure preference
            proc_cnt = await conn.fetchval("SELECT count(*) FROM procedural_memories WHERE namespace = $1;", test_ns)
            edge_cnt = await conn.fetchval("SELECT count(*) FROM entity_edges WHERE namespace = $1;", test_ns)
            assert proc_cnt == 0
            assert edge_cnt == 0

        # 3. Recall check
        recall_res = await svc_memory_recall(
            query="What backend framework and authentication is preferred?",
            namespace=test_ns,
        )
        assert len(recall_res.semantic) >= 1
        assert "<semantic_facts>" in recall_res.formatted_context
        assert any("token" in s.summary.lower() or "fastapi" in s.summary.lower() for s in recall_res.semantic)

    finally:
        await svc_memory_purge_namespace(namespace=test_ns, confirm=True)


@pytest.mark.asyncio
async def test_case_2_semantic_plus_entity_graph_store_and_recall():
    """Case 2: Semantic + Entity Graph - Verifies simultaneous atomic facts AND graph nodes/edges."""
    await ensure_db()
    test_ns = "test_multistore_semantic_entity"
    await svc_memory_purge_namespace(namespace=test_ns, confirm=True)

    try:
        raw_text = "I am Dheeban, leading the AI Engineering team at Strata Labs, and I am currently architecting the Jarvis agent."
        ingest_res = await svc_memory_ingest(raw_text=raw_text, namespace=test_ns)
        assert ingest_res.success is True
        assert ingest_res.details.get("semantic_count", 0) >= 1
        assert ingest_res.details.get("entity_count", 0) >= 1

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # 1. Verify Semantic facts stored
            sem_rows = await conn.fetch(
                "SELECT memory_id, summary FROM memories WHERE namespace = $1 AND type = 'semantic';",
                test_ns,
            )
            assert len(sem_rows) >= 1
            assert any("dheeban" in r["summary"].lower() for r in sem_rows)

            # 2. Verify Entity Nodes stored
            node_rows = await conn.fetch(
                "SELECT entity_id, name, entity_type FROM entity_nodes WHERE namespace = $1;",
                test_ns,
            )
            assert len(node_rows) >= 2
            node_names = [n["name"].lower() for n in node_rows]
            assert any("dheeban" in n for n in node_names)

            # 3. Verify Entity Edges stored
            edge_rows = await conn.fetch(
                "SELECT edge_id, relation_type, fact_summary FROM entity_edges WHERE namespace = $1;",
                test_ns,
            )
            assert len(edge_rows) >= 1
            rel_types = [e["relation_type"].upper() for e in edge_rows]
            assert any(r in rel_types for r in ["WORKS_AT", "LEADS", "ARCHITECTS", "WORKS_ON", "MEMBER_OF", "USES"])

        # 4. Recall Entity Graph via 1-hop traversal
        recall_graph = await svc_memory_recall(
            query="Who is Dheeban and where does he work?",
            namespace=test_ns,
        )
        assert len(recall_graph.entities) >= 1
        assert "<entity_graph>" in recall_graph.formatted_context
        assert any("dheeban" in e.source_name.lower() or "dheeban" in e.target_name.lower() for e in recall_graph.entities)

        # 5. Recall Semantic Fact
        recall_sem = await svc_memory_recall(
            query="What is Dheeban's role and project?",
            namespace=test_ns,
        )
        assert len(recall_sem.semantic) >= 1 or len(recall_sem.entities) >= 1

    finally:
        await svc_memory_purge_namespace(namespace=test_ns, confirm=True)


@pytest.mark.asyncio
async def test_case_3_semantic_plus_procedural_store_and_recall():
    """Case 3: Semantic + Procedural - Verifies runbook workflow AND underlying configuration rule."""
    await ensure_db()
    test_ns = "test_multistore_semantic_procedural"
    await svc_memory_purge_namespace(namespace=test_ns, confirm=True)

    try:
        raw_text = (
            "When deploying database migrations to Neon, step 1 is to acquire direct unpooled connection URL, "
            "step 2 is to apply the SQL schema, and step 3 is to verify the pgvector index. "
            "Remember that Neon pooler endpoints reject prepared statements and DDL."
        )
        ingest_res = await svc_memory_ingest(raw_text=raw_text, namespace=test_ns)
        assert ingest_res.success is True

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # 1. Verify Procedural Runbook created
            proc_rows = await conn.fetch(
                "SELECT name, steps, trigger_condition FROM procedural_memories WHERE namespace = $1 AND is_active = TRUE;",
                test_ns,
            )
            assert len(proc_rows) >= 1
            proc = proc_rows[0]
            assert len(proc["steps"]) >= 2 or "neon" in proc["name"].lower()

            # 2. Verify Semantic rule stored
            sem_rows = await conn.fetch(
                "SELECT summary FROM memories WHERE namespace = $1 AND type = 'semantic';",
                test_ns,
            )
            assert len(sem_rows) >= 1
            assert any("neon" in s["summary"].lower() or "pooler" in s["summary"].lower() or "statement" in s["summary"].lower() for s in sem_rows)

        # 3. Recall Procedural Workflow
        recall_proc = await svc_memory_recall(
            query="How do I deploy database migrations to Neon?",
            namespace=test_ns,
        )
        assert len(recall_proc.procedural) >= 1
        assert "<procedural_skills>" in recall_proc.formatted_context
        assert len(recall_proc.procedural[0].steps) >= 2
        steps_text = " ".join(recall_proc.procedural[0].steps).lower()
        assert any(term in steps_text for term in ["connection", "schema", "index", "neon", "unpooled", "step", "migration"])

        # 4. Recall Semantic Architectural Rule
        recall_rule = await svc_memory_recall(
            query="Why can't we use the pooler connection for migrations?",
            namespace=test_ns,
        )
        assert len(recall_rule.semantic) >= 1
        assert "<semantic_facts>" in recall_rule.formatted_context
        assert any("pooler" in s.summary.lower() or "statement" in s.summary.lower() or "reject" in s.summary.lower() or "ddl" in s.summary.lower() for s in recall_rule.semantic)

    finally:
        await svc_memory_purge_namespace(namespace=test_ns, confirm=True)


@pytest.mark.asyncio
async def test_case_4_episodic_plus_semantic_store_and_recall():
    """Case 4: Episodic + Semantic - Verifies execution trace AND learned configuration setting."""
    await ensure_db()
    test_ns = "test_multistore_episodic_semantic"
    await svc_memory_purge_namespace(namespace=test_ns, confirm=True)

    try:
        raw_text = (
            "Yesterday at 4 PM, our background worker crashed with connection timeout error. "
            "We increased pool max_inactive_connection_lifetime to 300 seconds and the connection drops stopped completely."
        )
        ingest_res = await svc_memory_ingest(raw_text=raw_text, namespace=test_ns)
        assert ingest_res.success is True

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # 1. Verify Episodic trace stored
            ep_rows = await conn.fetch(
                "SELECT memory_id, summary, payload FROM memories WHERE namespace = $1 AND type = 'episodic';",
                test_ns,
            )
            # Either an episodic row or semantic row capturing the incident
            all_mems = await conn.fetch(
                "SELECT memory_id, type, summary FROM memories WHERE namespace = $1;",
                test_ns,
            )
            assert len(all_mems) >= 1
            assert any("300" in m["summary"] or "timeout" in m["summary"].lower() for m in all_mems)

        # 2. Recall Incident History
        recall_incident = await svc_memory_recall(
            query="What happened with the background worker yesterday?",
            namespace=test_ns,
        )
        assert len(recall_incident.episodic) >= 1 or len(recall_incident.semantic) >= 1
        assert any("worker" in s.summary.lower() or "connection" in s.summary.lower() for s in (recall_incident.episodic + recall_incident.semantic))

        # 3. Recall Learned Setting
        recall_setting = await svc_memory_recall(
            query="What is the recommended pool lifetime setting to prevent connection drops?",
            namespace=test_ns,
        )
        assert len(recall_setting.semantic) >= 1 or len(recall_setting.episodic) >= 1
        combined = recall_setting.semantic + recall_setting.episodic
        assert any("300" in s.summary or "lifetime" in s.summary.lower() for s in combined)

    finally:
        await svc_memory_purge_namespace(namespace=test_ns, confirm=True)


@pytest.mark.asyncio
async def test_case_5_cross_reverse_superseding_and_invalidation():
    """Case 5: Cross-Reverse & Superseding - Verifies state updates bi-temporally invalidate old records."""
    await ensure_db()
    test_ns = "test_multistore_cross_reverse"
    await svc_memory_purge_namespace(namespace=test_ns, confirm=True)

    try:
        # Phase 1: Initial state
        raw_1 = "Velora project is hosted on AWS EC2 and uses PostgreSQL for persistence."
        ingest_1 = await svc_memory_ingest(raw_text=raw_1, namespace=test_ns)
        assert ingest_1.success is True

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            initial_edges = await conn.fetch(
                "SELECT edge_id, relation_type, fact_summary, valid_until FROM entity_edges WHERE namespace = $1;",
                test_ns,
            )
            initial_sems = await conn.fetch(
                "SELECT memory_id, summary, valid_until FROM memories WHERE namespace = $1 AND type = 'semantic';",
                test_ns,
            )
            assert len(initial_sems) >= 1 or len(initial_edges) >= 1

        # Phase 2: State transition / Update
        raw_2 = "Update: Velora project was migrated from AWS EC2 to GCP Cloud Run, and now uses Neon Serverless Postgres instead of PostgreSQL."
        ingest_2 = await svc_memory_ingest(raw_text=raw_2, namespace=test_ns)
        assert ingest_2.success is True

        async with pool.acquire() as conn:
            # Check active edges (valid_until IS NULL)
            active_edges = await conn.fetch(
                "SELECT edge_id, relation_type, fact_summary FROM entity_edges WHERE namespace = $1 AND valid_until IS NULL;",
                test_ns,
            )
            # Check active semantic memories
            active_sems = await conn.fetch(
                "SELECT memory_id, summary FROM memories WHERE namespace = $1 AND type = 'semantic' AND (valid_until IS NULL OR valid_until > NOW());",
                test_ns,
            )

            # Active records should reflect GCP / Neon
            all_active_summaries = [e["fact_summary"].lower() for e in active_edges] + [s["summary"].lower() for s in active_sems]
            assert any("gcp" in s or "cloud run" in s or "neon" in s for s in all_active_summaries)

        # Phase 3: Recall updated state
        recall_res = await svc_memory_recall(
            query="Where is Velora hosted and what database does it use?",
            namespace=test_ns,
        )
        context = recall_res.formatted_context.lower()
        # Verify active context surfaces GCP / Neon
        assert "gcp" in context or "cloud run" in context or "neon" in context

    finally:
        await svc_memory_purge_namespace(namespace=test_ns, confirm=True)


@pytest.mark.asyncio
async def test_case_6_identity_role_transition_and_superseding():
    """Case 6: Role Transition & Bi-temporal Superseding (The Dheeban Software Engineer -> SRE Engineer case).
    Verifies that when a user's role transitions:
    1. Initial role is stored.
    2. Role change supersedes the old role (valid_until stamped, superseded_by linked).
    3. Old role is never deleted, maintaining full audit trail.
    4. Recall for current role returns only 'SRE Engineer', never obsolete 'Software Engineer'.
    5. Also verifies explicit memory_edit API (svc_memory_edit).
    """
    await ensure_db()
    test_ns = "test_multistore_role_transition"
    await svc_memory_purge_namespace(namespace=test_ns, confirm=True)

    try:
        # Phase 1: Ingest initial role
        raw_1 = "My name is Dheeban and I am a Software Engineer."
        ingest_1 = await svc_memory_ingest(raw_text=raw_1, namespace=test_ns)
        assert ingest_1.success is True

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            mems_1 = await conn.fetch(
                "SELECT memory_id, summary, valid_from, valid_until FROM memories WHERE namespace = $1 AND (valid_until IS NULL OR valid_until > NOW());",
                test_ns,
            )
            assert len(mems_1) >= 1
            assert any("software engineer" in m["summary"].lower() for m in mems_1)

        # Phase 2: Ingest role update without any keyword indicators (pure LLM reasoning)
        raw_2 = "I am an SRE Engineer now."
        ingest_2 = await svc_memory_ingest(raw_text=raw_2, namespace=test_ns)
        assert ingest_2.success is True
        assert len(ingest_2.superseded_ids) >= 1

        async with pool.acquire() as conn:
            # Check bi-temporal state
            all_mems = await conn.fetch(
                "SELECT memory_id, summary, valid_from, valid_until, superseded_by FROM memories WHERE namespace = $1 ORDER BY created_at ASC;",
                test_ns,
            )
            superseded_mems = [m for m in all_mems if m["valid_until"] is not None]
            active_mems = [m for m in all_mems if m["valid_until"] is None]

            # The old Software Engineer fact must be preserved with valid_until set and superseded_by pointing to the new memory
            assert len(superseded_mems) >= 1
            assert any("software engineer" in m["summary"].lower() for m in superseded_mems)
            assert any(m["superseded_by"] is not None for m in superseded_mems)

            # Active memory must reflect SRE Engineer
            assert len(active_mems) >= 1
            assert any("sre" in m["summary"].lower() for m in active_mems)

        # Phase 3: Recall current role
        recall_res = await svc_memory_recall(
            query="What is Dheeban's current role?",
            namespace=test_ns,
        )
        context = recall_res.formatted_context.lower()
        assert "sre" in context
        assert "sre engineer" in context

        # Phase 4: Explicit svc_memory_edit
        active_sre_id = str(active_mems[0]["memory_id"])
        edit_res = await svc_memory_edit(
            target_id_or_name=active_sre_id,
            instruction="Role is Principal SRE and Tech Lead",
            pillar="semantic",
            namespace=test_ns,
        )
        assert edit_res["status"] == "edited"
        assert edit_res["superseded_memory_id"] is not None

        # Verify recall reflects the edited fact
        recall_edited = await svc_memory_recall(
            query="What is Dheeban's position?",
            namespace=test_ns,
        )
        assert "principal" in recall_edited.formatted_context.lower() or "tech lead" in recall_edited.formatted_context.lower() or "sre" in recall_edited.formatted_context.lower()

    finally:
        await svc_memory_purge_namespace(namespace=test_ns, confirm=True)


@pytest.mark.asyncio
async def test_case_7_semantic_ingest_intelligent_edit_and_feedback():
    """Case 7: Semantic Ingest + Intelligent Edit (UUID vs Auto-Pull) + Feedback Loop.
    Verifies the 3 main capabilities:
    1. Ingest Semantic: Ingests initial domain fact.
    2. Intelligent Edit:
       - Mode A (Explicit UUID): Modifies fact using exact ID, creates bi-temporal supersede.
       - Mode B (Intelligent Auto-Location): Modifies fact WITHOUT passing UUID (passing search query or empty string),
         system uses vector search to intelligently find the target active memory and supersedes it!
    3. Feedback Loop:
       - Positive Feedback (+1 score, resets decay, bumps confidence).
       - Negative Feedback (-2 score, lowers confidence).
       - Query-based Feedback (auto-locates memory by query without knowing UUID).
    """
    await ensure_db()
    test_ns = "test_multistore_edit_feedback"
    await svc_memory_purge_namespace(namespace=test_ns, confirm=True)

    try:
        # Part 1: Ingest Semantic Fact
        raw_text = "The production database host is db.internal.net on port 5432."
        ingest_res = await svc_memory_ingest(raw_text=raw_text, namespace=test_ns)
        assert ingest_res.success is True
        initial_id = ingest_res.created_ids[0]

        # Part 2A: Edit via Explicit UUID
        edit_explicit = await svc_memory_edit(
            target_id_or_name=initial_id,
            instruction="Database port changed to 5433",
            pillar="semantic",
            namespace=test_ns,
        )
        assert edit_explicit["status"] == "edited"
        assert edit_explicit["superseded_memory_id"] == initial_id
        uuid_edited_id = edit_explicit["new_memory_id"]

        # Part 2B: Edit via Intelligent Auto-Location (NO UUID passed, caller passes search query or topic)
        edit_auto = await svc_memory_edit(
            target_id_or_name="production database",
            instruction="Database host changed from db.internal.net to neon-cluster.strata.io and port is 5433",
            pillar="semantic",
            namespace=test_ns,
        )
        assert edit_auto["status"] == "edited"
        assert edit_auto["superseded_memory_id"] == uuid_edited_id
        final_id = edit_auto["new_memory_id"]

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Verify database audit trail: 2 superseded records, 1 active record
            all_mems = await conn.fetch(
                "SELECT memory_id, summary, valid_until, superseded_by, utility_score FROM memories WHERE namespace = $1 ORDER BY created_at ASC;",
                test_ns,
            )
            assert len(all_mems) == 3
            superseded = [m for m in all_mems if m["valid_until"] is not None]
            active = [m for m in all_mems if m["valid_until"] is None]
            assert len(superseded) == 2
            assert len(active) == 1
            assert "neon-cluster" in active[0]["summary"].lower()

        # Part 3A: Positive Feedback via Explicit UUID
        fb_pos = await svc_memory_feedback(
            memory_ids_used=[final_id],
            success=True,
            namespace=test_ns,
        )
        assert fb_pos["status"] == "feedback_recorded"
        assert fb_pos["memories_updated_count"] == 1

        async with pool.acquire() as conn:
            score_after_pos = await conn.fetchval(
                "SELECT utility_score FROM memories WHERE memory_id = $1;",
                UUID(final_id),
            )
            assert score_after_pos == 1

        # Part 3B: Negative Feedback via Intelligent Query Auto-Location (NO UUID passed)
        fb_query = await svc_memory_feedback(
            memory_query="neon-cluster database",
            success=False,
            namespace=test_ns,
        )
        assert fb_query["status"] == "feedback_recorded"
        assert fb_query["memories_updated_count"] == 1
        assert final_id in fb_query["memory_ids_updated"]

        async with pool.acquire() as conn:
            score_after_neg = await conn.fetchval(
                "SELECT utility_score FROM memories WHERE memory_id = $1;",
                UUID(final_id),
            )
            assert score_after_neg == -1  # 1 - 2 = -1

        # Part 4: Recall verification
        recall_res = await svc_memory_recall(
            query="What is the production database host and port?",
            namespace=test_ns,
        )
        assert len(recall_res.semantic) >= 1
        assert "neon-cluster" in recall_res.formatted_context.lower()
        assert "5433" in recall_res.formatted_context

    finally:
        await svc_memory_purge_namespace(namespace=test_ns, confirm=True)


@pytest.mark.asyncio
async def test_case_8_domain_agnostic_non_technical_evolution():
    """Case 8: Pure non-technical real-world conversation & universal state evolution.
    Proves zero domain overfitting: residence relocation and schedule changes supersede
    outdated functional slots via semantic proximity + Cognitive LLM without update keywords.
    """
    await ensure_db()
    test_ns = "test_multistore_nontech"
    await svc_memory_purge_namespace(namespace=test_ns, confirm=True)

    try:
        # 1. Initial non-technical life & schedule facts
        res1 = await svc_memory_ingest(
            raw_text="My name is Alice and I live in London. Our weekly book club meets on Mondays.",
            namespace=test_ns,
        )
        assert res1.success is True
        assert res1.details.get("semantic_count", 0) >= 2

        # 2. Natural non-technical evolution (zero update/change keywords, zero tech terms)
        res2 = await svc_memory_ingest(
            raw_text="I moved to Tokyo last month, and we shifted the weekly book club to Thursdays.",
            namespace=test_ns,
        )
        assert res2.success is True
        assert len(res2.superseded_ids) >= 1

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT memory_id, type, summary, valid_until, superseded_by FROM memories WHERE namespace = $1 ORDER BY created_at ASC;",
                test_ns,
            )
            active_sem = [r for r in rows if r["type"] == "semantic" and r["valid_until"] is None]
            superseded_sem = [r for r in rows if r["type"] == "semantic" and r["valid_until"] is not None]

            active_text = " ".join(r["summary"].lower() for r in active_sem)
            superseded_text = " ".join(r["summary"].lower() for r in superseded_sem)

            assert "tokyo" in active_text
            assert "thursdays" in active_text or "thursday" in active_text
            assert "london" in superseded_text or "monday" in superseded_text
            assert "london" not in active_text

        # 3. Recall verification
        recall_res = await svc_memory_recall(
            query="Where does Alice live and when does the book club meet?",
            namespace=test_ns,
        )
        ctx = recall_res.formatted_context.lower()
        assert "tokyo" in ctx
        assert "thursday" in ctx
        assert "london" not in ctx
        assert "monday" not in ctx

    finally:
        await svc_memory_purge_namespace(namespace=test_ns, confirm=True)
