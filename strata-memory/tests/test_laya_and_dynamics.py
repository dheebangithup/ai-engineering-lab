import pytest
from strata.laya import laya_engine
from strata.models import IngestRequest, RecallRequest


def test_laya_simple_semantic_classification():
    """Verify Laya accurately classifies simple preference as semantic."""
    text = "I prefer Python 3.12 with asyncpg and FastAPI for all backends."
    decision = laya_engine.evaluate(
        raw_text=text,
        raw_embedding=[0.0] * 768,
        context_data={},
    )
    assert decision.complexity == "simple"
    assert decision.primary_pillar == "semantic"
    assert decision.extraction_plan is not None
    assert len(decision.extraction_plan.semantic_ops) == 1
    assert decision.extraction_plan.semantic_ops[0].action == "ADD"
    assert "python" in decision.extraction_plan.semantic_ops[0].tags


def test_laya_simple_episodic_classification():
    """Verify Laya classifies build/run failure as episodic."""
    text = "Deployment to Neon failed at 3pm with SSL connection refused error."
    decision = laya_engine.evaluate(
        raw_text=text,
        raw_embedding=[0.0] * 768,
        context_data={},
    )
    assert decision.complexity == "simple"
    assert decision.primary_pillar == "episodic"
    assert decision.extraction_plan is not None
    assert len(decision.extraction_plan.episodic_ops) == 1
    assert decision.extraction_plan.episodic_ops[0].success is False


def test_laya_entity_relation_classification():
    """Verify Laya detects graph relationships (e.g. USES, RUNS_ON)."""
    text = "Strata uses Neon for database persistence."
    decision = laya_engine.evaluate(
        raw_text=text,
        raw_embedding=[0.0] * 768,
        context_data={},
    )
    assert decision.complexity == "simple"
    assert decision.primary_pillar == "entity"
    assert decision.extraction_plan is not None
    assert len(decision.extraction_plan.entity_ops) == 1
    op = decision.extraction_plan.entity_ops[0]
    assert op.relation_type == "USES"
    assert op.source_name == "Strata"
    assert op.target_name == "Neon"


def test_laya_complex_multi_pillar_routing():
    """Verify Laya detects multi-pillar statements and flags as complex for the LLM."""
    text = (
        "We migrated from AWS to GCP last week. The deploy process broke because "
        "the old runbook used aws-cli. However, we updated the credentials and also remember that "
        "Dheeban maintains the GCP project. Next step is to verify the migrations."
    )
    decision = laya_engine.evaluate(
        raw_text=text,
        raw_embedding=[0.0] * 768,
        context_data={},
    )
    assert decision.complexity == "complex"
    assert decision.extraction_plan is None  # Delegates to Generative Small LLM


def test_laya_auto_supersede_detection():
    """Verify Laya identifies updates that supersede existing memories."""
    text = "Update: We changed default database from SQLite to Neon Postgres."
    context_data = {
        "existing_semantic_memories": [
            {"id": "11111111-2222-3333-4444-555555555555", "summary": "Default database is SQLite."}
        ]
    }
    decision = laya_engine.evaluate(
        raw_text=text,
        raw_embedding=[0.0] * 768,
        context_data=context_data,
    )
    assert decision.is_supersede is True
    assert decision.supersede_target_id == "11111111-2222-3333-4444-555555555555"
    assert decision.extraction_plan.semantic_ops[0].action == "SUPERSEDE"
    assert decision.extraction_plan.semantic_ops[0].supersede_memory_id == "11111111-2222-3333-4444-555555555555"


def test_dynamic_recall_and_ingest_models():
    """Verify dynamic parameters are properly handled on request models."""
    recall_req = RecallRequest(
        query="What database is used?",
        match_threshold=0.55,
        min_score=0.02,
        similarity_threshold=0.60,
    )
    assert recall_req.match_threshold == 0.55
    assert recall_req.min_score == 0.02
    assert recall_req.similarity_threshold == 0.60

    ingest_req = IngestRequest(
        raw_text="Test fact",
        contradiction_threshold=0.90,
        use_decision_model=True,
        laya_mode="hybrid",
    )
    assert ingest_req.contradiction_threshold == 0.90
    assert ingest_req.use_decision_model is True
    assert ingest_req.laya_mode == "hybrid"


def test_laya_signal_gating_filler():
    """Verify Write Policy Signal Gate drops low-signal conversational filler."""
    fillers = [
        "thanks, got it!",
        "okay",
        "cool",
        "hi",
        "sounds good",
        "perfect!",
    ]
    for text in fillers:
        decision = laya_engine.evaluate(
            raw_text=text,
            raw_embedding=[0.0] * 768,
            context_data={},
        )
        assert decision.is_signal is False, f"Expected '{text}' to be dropped by signal gate"


def test_laya_signal_gating_valid_facts():
    """Verify Write Policy Signal Gate accepts legitimate factual statements."""
    facts = [
        "The staging database runs on port 5432.",
        "Dheeban prefers poetry over prose.",
        "PostgreSQL max connections is set to 100.",
    ]
    for text in facts:
        decision = laya_engine.evaluate(
            raw_text=text,
            raw_embedding=[0.0] * 768,
            context_data={},
        )
        assert decision.is_signal is True, f"Expected '{text}' to pass signal gate"


def test_laya_query_intent_classification():
    """Verify Retrieval Policy Gate dynamically routes queries to appropriate pillars."""
    proc_query = "How do I deploy the authentication service to staging?"
    assert "procedural" in laya_engine.classify_query_intent(proc_query)

    graph_query = "What infrastructure does PaymentService run on?"
    assert "entity" in laya_engine.classify_query_intent(graph_query)

    episodic_query = "Did the database migration fail yesterday?"
    assert "episodic" in laya_engine.classify_query_intent(episodic_query)

    semantic_query = "What is the database password for staging?"
    assert "semantic" in laya_engine.classify_query_intent(semantic_query)


def test_working_memory_tool_pinning_and_budget_eviction():
    """Verify Short-Term Working Memory pins active tool results to eliminate Eviction Policy Bug."""
    from strata.working_memory import WorkingMemoryManager

    mgr = WorkingMemoryManager(default_max_tokens=50)

    # 1. Add conversation turns
    mgr.add_message("test_ns", "sess_1", "user", "Run the deployment check.", turn_id=1)
    mgr.add_message("test_ns", "sess_1", "assistant", "Checking server status now.", turn_id=2)

    # 2. Add protected tool output (e.g. server check output)
    tool_out = mgr.add_tool_output(
        namespace="test_ns",
        session_id="sess_1",
        tool_call_id="call_check_1",
        tool_name="server_status",
        content="STATUS=OK, CLUSTER=US-EAST-1, NODES=4",
        protected=True,
    )
    assert tool_out.protected is True

    # 3. Add more conversation turns that exceed token budget
    mgr.add_message("test_ns", "sess_1", "assistant", "Server is healthy. Proceeding with phase 2.", turn_id=4)
    mgr.add_message("test_ns", "sess_1", "user", "What were the node details again?", turn_id=5)

    # Enforce budget of 25 tokens (small budget)
    kept = mgr.enforce_budget("test_ns", "sess_1", max_tokens=25)

    # Tool output MUST be preserved because protected=True!
    tool_items = [it for it in kept if it.tool_call_id == "call_check_1"]
    assert len(tool_items) == 1
    assert tool_items[0].protected is True

    # 4. Unprotect tool output once reasoning finishes
    mgr.unprotect_tool("test_ns", "sess_1", "call_check_1")
    assert tool_items[0].protected is False

    # 5. Now enforce very strict budget (5 tokens)
    kept_after = mgr.enforce_budget("test_ns", "sess_1", max_tokens=5)
    # The unprotected tool output can now be evicted if necessary
    assert sum(it.token_count for it in kept_after) <= 15


@pytest.mark.asyncio
async def test_signal_gate_and_fact_reaffirmation_e2e():
    """Verify Write Policy Signal Gate drops filler in DB and Fact Reaffirmation updates reaffirmed_at."""
    from strata.db import get_db_pool, close_db_pool
    from strata.service import svc_memory_ingest, svc_memory_purge_namespace
    from uuid import UUID

    test_ns = "test_laya_policy_gates"
    await svc_memory_purge_namespace(namespace=test_ns, confirm=True)

    try:
        # 1. Test Signal Gate on conversational filler
        filler_res = await svc_memory_ingest(
            raw_text="Thanks, got it!",
            namespace=test_ns,
        )
        assert filler_res.details.get("mode") == "laya_signal_filtered"
        assert len(filler_res.created_ids) == 0

        # Verify DB has 0 memories
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            cnt = await conn.fetchval("SELECT count(*) FROM memories WHERE namespace = $1;", test_ns)
            assert cnt == 0, f"Expected 0 memories written for filler, found {cnt}"

        # 2. Ingest initial factual memory
        fact_text = "The staging database port is 5432 and SSL is strictly enforced."
        ingest_1 = await svc_memory_ingest(
            raw_text=fact_text,
            namespace=test_ns,
            fast_mode=True,
        )
        assert len(ingest_1.created_ids) == 1
        initial_id = ingest_1.created_ids[0]

        async with pool.acquire() as conn:
            row_1 = await conn.fetchrow(
                "SELECT access_count, reaffirmed_at FROM memories WHERE memory_id = $1;",
                UUID(initial_id),
            )
            assert row_1["access_count"] == 0
            assert row_1["reaffirmed_at"] is None

        # 3. Reaffirm the same fact
        ingest_2 = await svc_memory_ingest(
            raw_text=fact_text,
            namespace=test_ns,
            fast_mode=True,
        )
        # Should reaffirm existing row rather than creating a duplicate
        assert ingest_2.created_ids[0] == initial_id

        async with pool.acquire() as conn:
            row_2 = await conn.fetchrow(
                "SELECT access_count, reaffirmed_at FROM memories WHERE memory_id = $1;",
                UUID(initial_id),
            )
            assert row_2["access_count"] == 1
            assert row_2["reaffirmed_at"] is not None

            # Total memories count in DB should still be exactly 1 (no duplicate pollution)
            total_cnt = await conn.fetchval("SELECT count(*) FROM memories WHERE namespace = $1;", test_ns)
            assert total_cnt == 1

    finally:
        await svc_memory_purge_namespace(namespace=test_ns, confirm=True)
        await close_db_pool()
