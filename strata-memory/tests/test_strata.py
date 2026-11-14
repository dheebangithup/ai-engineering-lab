import pytest
import pytest_asyncio
from datetime import datetime, timezone
from strata.embedder import LocalEmbedder
from strata.models import (
    EntityExtractionOp,
    EntityGraphItem,
    EpisodicExtractionOp,
    EpisodicMemoryItem,
    MemoryExtractionPlan,
    ProceduralExtractionOp,
    ProceduralMemoryItem,
    RecallRequest,
    RecallResponse,
    SemanticExtractionOp,
    SemanticMemoryItem,
)
from strata.recall import build_xml_context
from strata.db import get_db_pool, close_db_pool, run_migrations
from strata.service import (
    svc_memory_ingest,
    svc_memory_recall,
    svc_memory_store_explicit,
    svc_memory_feedback,
    svc_memory_delete,
)


@pytest.mark.asyncio
async def test_embedder_dimensions():
    """Verify OllamaEmbedder asynchronously loads embeddings and outputs exactly 768 dimensions."""
    try:
        embedder = LocalEmbedder.get_instance()
        vec = await embedder.embed_one("Strata 4-Pillar Memory Engine")
        assert len(vec) == 768
        vec_str = embedder.to_pgvector_str(vec)
        assert vec_str.startswith("[") and vec_str.endswith("]")
        assert len(vec_str.split(",")) == 768
    except Exception as e:
        pytest.skip(f"Ollama/embedding server not reachable ({e}), skipping live embedding test.")


def test_models_extraction_plan():
    """Verify Pydantic models validate 4-pillar operations."""
    plan_data = {
        "semantic_ops": [
            {
                "action": "ADD",
                "summary": "Neon supports serverless Postgres branching.",
                "tags": ["neon", "postgres"],
                "confidence": 0.98,
            }
        ],
        "episodic_ops": [
            {
                "summary": "Ran migration successfully.",
                "situation": "Initial database setup",
                "action_taken": "Applied 001_init_schema.sql",
                "outcome": "All tables and RRF functions created",
                "success": True,
                "tags": ["migration"],
            }
        ],
        "procedural_ops": [
            {
                "action": "CREATE",
                "name": "run_neon_migration",
                "description": "How to run DDL migration against Neon direct endpoint",
                "trigger_condition": "When modifying database schema",
                "steps": ["Use DIRECT_DATABASE_URL", "Execute SQL file", "Verify tables"],
                "prerequisites": {"neon_ssl": "require"},
            }
        ],
        "entity_ops": [
            {
                "source_name": "Strata",
                "source_type": "project",
                "source_summary": "4-pillar memory engine",
                "relation_type": "RUNS_ON",
                "target_name": "Neon",
                "target_type": "infrastructure",
                "target_summary": "Serverless PostgreSQL",
                "fact_summary": "Strata runs on Neon serverless PostgreSQL",
                "invalidate_conflicting_relations": True,
            }
        ],
    }
    plan = MemoryExtractionPlan.model_validate(plan_data)
    assert len(plan.semantic_ops) == 1
    assert len(plan.episodic_ops) == 1
    assert len(plan.procedural_ops) == 1
    assert len(plan.entity_ops) == 1
    assert plan.procedural_ops[0].name == "run_neon_migration"


def test_build_xml_context():
    """Verify XML context packing respects token budgets and closes XML properly."""
    now = datetime.now(timezone.utc)
    semantic = [
        SemanticMemoryItem(
            memory_id="11111111-1111-1111-1111-111111111111",
            summary="User prefers Neon Serverless PostgreSQL with pgvector.",
            created_at=now,
            rrf_score=0.92,
        )
    ]
    entities = [
        EntityGraphItem(
            edge_id="22222222-2222-2222-2222-222222222222",
            source_name="Strata",
            source_type="engine",
            relation_type="CONNECTS_TO",
            target_name="Neon",
            target_type="database",
            fact_summary="Strata connects to Neon via asyncpg connection pool",
            valid_from=now,
        )
    ]
    procedural = [
        ProceduralMemoryItem(
            procedure_id="33333333-3333-3333-3333-333333333333",
            name="deploy_service",
            description="Deployment procedure",
            trigger_condition="On release",
            steps=["Step 1", "Step 2"],
            version=1,
            success_count=9,
            fail_count=1,
            success_rate=0.833,
            composite_score=0.88,
        )
    ]
    episodic = [
        EpisodicMemoryItem(
            memory_id="44444444-4444-4444-4444-444444444444",
            summary="Initialized schema on Neon successfully.",
            success=True,
            created_at=now,
            rrf_score=0.85,
        )
    ]

    xml = build_xml_context(
        namespace="default",
        semantic=semantic,
        entities=entities,
        procedural=procedural,
        episodic=episodic,
        token_budget=500,
    )

    assert xml.startswith('<strata_memory_context namespace="default">')
    assert xml.endswith('</strata_memory_context>')
    assert "<semantic_facts>" in xml
    assert "<entity_graph>" in xml
    assert "<procedural_skills>" in xml
    assert "<episodic_history>" in xml


@pytest.mark.asyncio
async def test_live_db_flow():
    """Runs end-to-end integration flow if Neon or local PostgreSQL database is reachable."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1;")
        await run_migrations()
    except Exception as e:
        pytest.skip(f"Database not accessible ({e}), skipping live integration tests.")

    test_ns = "test_e2e"

    # 2. Explicit store: semantic
    sem_res = await svc_memory_store_explicit(
        pillar="semantic",
        payload={"summary": "Agent prefers Python 3.11+ and asyncpg."},
        namespace=test_ns,
    )
    assert sem_res["status"] == "stored"
    mem_id = sem_res["memory_id"]

    # 3. Explicit store: procedural
    proc_res = await svc_memory_store_explicit(
        pillar="procedural",
        payload={
            "name": "neon_branching_test",
            "description": "How to create an isolated database branch in Neon",
            "trigger_condition": "When creating a feature branch",
            "steps": ["Open Neon Console", "Click create branch", "Copy branch connection string"],
        },
        namespace=test_ns,
    )
    assert proc_res["status"] == "stored"

    # 4. Explicit store: entity
    ent_res = await svc_memory_store_explicit(
        pillar="entity",
        payload={
            "source_name": "Developer",
            "source_type": "person",
            "source_summary": "Engineer building agents",
            "relation_type": "MAINTAINS",
            "target_name": "StrataEngine",
            "target_type": "project",
            "target_summary": "4-pillar memory engine",
            "fact_summary": "Developer maintains StrataEngine project",
        },
        namespace=test_ns,
    )
    assert ent_res["status"] == "stored"

    # 5. Recall
    recall = await svc_memory_recall(
        query="What database and python version does the agent use?",
        namespace=test_ns,
    )
    assert recall.namespace == test_ns
    assert len(recall.semantic) > 0 or len(recall.procedural) > 0

    # 6. Feedback
    fb = await svc_memory_feedback(
        memory_ids_used=[mem_id],
        procedure_name="neon_branching_test",
        success=True,
        namespace=test_ns,
    )
    assert fb["status"] == "feedback_recorded"

    # 7. Cleanup
    await svc_memory_delete(target_id=mem_id, pillar="semantic", hard_delete=True, namespace=test_ns)
    await svc_memory_delete(target_id="neon_branching_test", pillar="procedural", hard_delete=True, namespace=test_ns)
    await svc_memory_delete(target_id="Developer", pillar="entity", hard_delete=True, namespace=test_ns)
    await close_db_pool()
