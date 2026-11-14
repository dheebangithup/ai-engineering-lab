"""Strata 4-Pillar Memory Engine Demo Script.

Demonstrates:
1. Storing facts, procedures, and entities across the 4 pillars.
2. Running deterministic hybrid recall (<15ms, zero-LLM).
3. Viewing the token-budgeted XML context block.
4. Applying utility score feedback.
5. Ingesting raw natural language.
"""

import asyncio
import json
from strata.service import (
    svc_memory_feedback,
    svc_memory_ingest,
    svc_memory_purge_namespace,
    svc_memory_recall,
    svc_memory_store_explicit,
)
from strata.db import close_db_pool


async def main():
    print("=" * 70)
    print("🧠 STRATA 4-PILLAR COGNITIVE MEMORY ENGINE - LIVE DEMO")
    print("=" * 70)

    namespace = "demo"

    # ------------------------------------------------------------------------
    # Step 1: Explicitly Store memories across pillars
    # ------------------------------------------------------------------------
    print("\n[1] Storing memories across pillars into Neon PostgreSQL...")

    # Pillar 1: Semantic
    sem_res = await svc_memory_store_explicit(
        pillar="semantic",
        payload={
            "summary": "User prefers using Neon Serverless Postgres with pgvector for low-latency vector search.",
            "tags": ["database", "neon", "pgvector"],
        },
        namespace=namespace,
    )
    print(f"  ✓ Stored Semantic Fact: {sem_res['memory_id']}")
    mem_id = sem_res["memory_id"]

    # Pillar 3: Procedural
    proc_res = await svc_memory_store_explicit(
        pillar="procedural",
        payload={
            "name": "neon_migration_runbook",
            "description": "How to execute DDL schema migrations against Neon",
            "trigger_condition": "When running database migrations",
            "steps": [
                "Ensure DIRECT_DATABASE_URL is used instead of pooled URL",
                "Execute 001_init_schema.sql with asyncpg (statement_cache_size=0)",
                "Verify pgvector extension and HNSW indexes",
            ],
            "prerequisites": {"sslmode": "require"},
        },
        namespace=namespace,
    )
    print(f"  ✓ Stored Procedural Skill: {proc_res['procedure_id']}")

    # Pillar 4: Entity Graph
    ent_res = await svc_memory_store_explicit(
        pillar="entity",
        payload={
            "source_name": "Strata",
            "source_type": "software",
            "source_summary": "Cognitive memory engine",
            "relation_type": "DEPLOYED_ON",
            "target_name": "Neon",
            "target_type": "cloud_service",
            "target_summary": "Serverless PostgreSQL with pgvector",
            "fact_summary": "Strata is deployed on Neon Serverless PostgreSQL",
        },
        namespace=namespace,
    )
    print(f"  ✓ Stored Entity Relation: {ent_res['edge_id']}")

    # ------------------------------------------------------------------------
    # Step 2: Deterministic Hybrid Recall (<15ms, Zero-LLM)
    # ------------------------------------------------------------------------
    query = "What database does the user prefer and how do we run migrations?"
    print(f"\n[2] Performing deterministic recall for query: '{query}'")

    recall = await svc_memory_recall(
        query=query,
        namespace=namespace,
        top_k=3,
        token_budget=1000,
    )

    print(f"  ✓ Recall complete! Found:")
    print(f"    - Semantic Facts: {len(recall.semantic)}")
    print(f"    - Procedural Skills: {len(recall.procedural)}")
    print(f"    - Entity Triples: {len(recall.entities)}")
    print(f"    - Approx Tokens: {recall.token_count_approx}")

    print("\n--- Formatted Context for Caller LLM Budget ---")
    print(recall.formatted_context)
    print("-------------------------------------------------")

    # ------------------------------------------------------------------------
    # Step 3: Record Feedback (Utility Score Bumping)
    # ------------------------------------------------------------------------
    print("\n[3] Submitting execution feedback (Agent successfully used memories)...")
    fb_res = await svc_memory_feedback(
        memory_ids_used=[mem_id],
        procedure_name="neon_migration_runbook",
        success=True,
        namespace=namespace,
    )
    print(f"  ✓ Feedback recorded: {json.dumps(fb_res)}")

    # ------------------------------------------------------------------------
    # Step 4: Autonomous Ingest (Small LLM Router or Fallback)
    # ------------------------------------------------------------------------
    print("\n[4] Testing memory ingest with unstructured text...")
    ingest_res = await svc_memory_ingest(
        raw_text="Dheeban is the lead architect working on the Strata AI memory system.",
        namespace=namespace,
        fast_mode=True,  # deterministic fast mode
    )
    print(f"  ✓ Ingest result: {ingest_res.model_dump_json(indent=2)}")

    # ------------------------------------------------------------------------
    # Step 5: Database Cleanup (Leave pristine clean slate)
    # ------------------------------------------------------------------------
    print("\n[5] Cleaning up demo namespace from database...")
    purge_res = await svc_memory_purge_namespace(namespace=namespace, confirm=True)
    print(f"  ✓ Clean slate confirmed: purged {purge_res.deleted_counts}")

    await close_db_pool()
    print("\n" + "=" * 70)
    print("✨ Live Demo Completed Successfully!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
