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
    )
    assert ingest_req.contradiction_threshold == 0.90
    assert ingest_req.use_decision_model is True
