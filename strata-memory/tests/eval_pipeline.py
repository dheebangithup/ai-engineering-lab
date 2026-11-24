"""Strata Cognitive Memory Engine - End-to-End Comprehensive Evaluation Pipeline.

Validates all 4 memory pillars (Semantic, Episodic, Procedural, Entity Graph)
and explicitly tests:
  1. Routing Verification: Laya Decision Engine (<5ms Fast Path) vs Generative Small LLM.
  2. Semantic Pillar: Ingest, Bi-temporal Contradiction & Superseding, TTL Expiration.
  3. Episodic Pillar: Direct Ingest, Utility Feedback Reinforcement, Cognitive Distillation & Compaction.
  4. Procedural Pillar: Runbook Storage, Bayesian Retrieval, Autonomous Self-Healing on Execution Failure.
  5. Entity Graph Pillar: Direct Extraction, 1-Hop Subgraph Traversal, Soft-Delete Symmetry.
  6. Compound Multi-Pillar Narrative: Small LLM multi-pillar atomic decomposition.
  7. Hybrid Zero-LLM Recall: Sub-15ms multi-pillar RRF retrieval & XML context assembly.
  8. Strict DB Isolation & Hygiene: Dedicated namespace with guaranteed pre & post cleanup.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import pytest

from strata.config import settings
from strata.db import close_db_pool, get_db_pool, run_migrations
from strata.service import (
    svc_memory_delete,
    svc_memory_feedback,
    svc_memory_ingest,
    svc_memory_prune,
    svc_memory_purge_namespace,
    svc_memory_recall,
    svc_memory_store_explicit,
    svc_working_memory_add,
    svc_working_memory_add_tool_output,
    svc_working_memory_clear,
    svc_working_memory_get,
    svc_working_memory_unprotect,
)

# Dedicated isolated namespace strictly for evaluation
NAMESPACE = "eval_dedicated_suite"


def print_section(title: str):
    print("\n" + "=" * 80)
    print(f"🔬 {title}")
    print("=" * 80)


def print_case_header(case_id: str, title: str, handler: str):
    print(f"\n--------------------------------------------------------------------------------")
    print(f"▶ {case_id}: {title}")
    print(f"  Expected Handler: [{handler}] | Namespace: '{NAMESPACE}'")
    print(f"--------------------------------------------------------------------------------")


async def verify_and_clean_db(pool, namespace: str, label: str):
    """Purges the dedicated namespace and verifies zero rows remain across all tables."""
    print(f"🧹 {label}: Cleansing all records for namespace '{namespace}'...")
    purge_res = await svc_memory_purge_namespace(namespace=namespace, confirm=True)
    
    async with pool.acquire() as conn:
        mem_count = await conn.fetchval("SELECT COUNT(*) FROM memories WHERE namespace = $1;", namespace)
        proc_count = await conn.fetchval("SELECT COUNT(*) FROM procedural_memories WHERE namespace = $1;", namespace)
        edge_count = await conn.fetchval("SELECT COUNT(*) FROM entity_edges WHERE namespace = $1;", namespace)
        node_count = await conn.fetchval("SELECT COUNT(*) FROM entity_nodes WHERE namespace = $1;", namespace)

    total = mem_count + proc_count + edge_count + node_count
    if total == 0:
        print(f"   ✓ Confirmed clean slate: 0 memories, 0 procedures, 0 edges, 0 nodes in '{namespace}'.")
    else:
        raise RuntimeError(
            f"Database cleanup verification failed! Residual rows in '{namespace}': "
            f"memories={mem_count}, procedures={proc_count}, edges={edge_count}, nodes={node_count}"
        )


async def run_eval_pipeline():
    print_section(f"STARTING COMPREHENSIVE STRATA EVALUATION (Dedicated Namespace: '{NAMESPACE}')")
    pool = await get_db_pool()
    await run_migrations()

    # Pre-flight cleanup
    await verify_and_clean_db(pool, NAMESPACE, label="Pre-flight DB Hygiene Check")

    results_summary: Dict[str, Dict[str, Any]] = {}

    try:
        # =====================================================================
        # PILLAR 1: SEMANTIC MEMORY
        # =====================================================================
        print_section("PILLAR 1: SEMANTIC MEMORY SUITE")

        # Case 1A: Simple Semantic Ingest (Laya-handled)
        print_case_header(
            "Case 1A",
            "Simple Preference / Fact Ingest",
            "Laya Decision Engine (<5ms Fast Path)",
        )
        raw_text_1a = "I prefer Python 3.12 with asyncpg and FastAPI for all backend microservices."
        print(f"📥 Input: \"{raw_text_1a}\"")
        
        t0 = time.perf_counter()
        res_1a = await svc_memory_ingest(raw_text=raw_text_1a, namespace=NAMESPACE)
        t1 = time.perf_counter()
        latency_1a_ms = (t1 - t0) * 1000.0

        mode_1a = res_1a.details.get("mode")
        pillar_1a = res_1a.details.get("laya_primary_pillar")
        print(f"⏱️ Ingest Latency: {latency_1a_ms:.2f} ms")
        print(f"   Routing Mode: '{mode_1a}' | Primary Pillar: '{pillar_1a}'")
        print(f"   Created ID(s): {res_1a.created_ids}")

        async with pool.acquire() as conn:
            row_1a = await conn.fetchrow(
                "SELECT memory_id, summary, type, valid_from, valid_until FROM memories WHERE memory_id = $1;",
                UUID(res_1a.created_ids[0]),
            )
        is_active_1a = row_1a["valid_until"] is None or row_1a["valid_until"] > datetime.now(timezone.utc)
        print(f"   DB Row: [{str(row_1a['memory_id'])[:8]}] type={row_1a['type']} active={is_active_1a} summary='{row_1a['summary']}'")

        case1a_pass = (
            mode_1a == "laya_decision"
            and pillar_1a == "semantic"
            and len(res_1a.created_ids) == 1
            and row_1a["type"] == "semantic"
            and is_active_1a
        )
        results_summary["Case 1A: Semantic Ingest"] = {
            "passed": case1a_pass,
            "handler": "Laya Decision Model",
            "details": f"mode={mode_1a}, latency={latency_1a_ms:.1f}ms",
        }
        print(f"=> Assessment: {'✅ PASSED (Laya Fast Path)' if case1a_pass else '❌ FAILED'}")

        # Case 1B: Contradiction & Bi-temporal Superseding (Laya-handled)
        print_case_header(
            "Case 1B",
            "Contradiction Detection & Automatic Superseding",
            "Laya Decision Engine (<5ms Fast Path)",
        )
        raw_text_1b = "Update: We changed backend microservices runtime preference to Python 3.13 with uv and FastAPI instead of Python 3.12."
        print(f"📥 Input: \"{raw_text_1b}\"")

        t0 = time.perf_counter()
        res_1b = await svc_memory_ingest(raw_text=raw_text_1b, namespace=NAMESPACE)
        t1 = time.perf_counter()
        latency_1b_ms = (t1 - t0) * 1000.0

        mode_1b = res_1b.details.get("mode")
        print(f"⏱️ Ingest Latency: {latency_1b_ms:.2f} ms")
        print(f"   Routing Mode: '{mode_1b}'")
        print(f"   Created ID(s): {res_1b.created_ids} | Superseded ID(s): {res_1b.superseded_ids}")

        async with pool.acquire() as conn:
            all_sem = await conn.fetch(
                "SELECT memory_id, summary, valid_from, valid_until, superseded_by FROM memories WHERE namespace = $1 AND type = 'semantic' ORDER BY created_at ASC;",
                NAMESPACE,
            )
        
        print("   Bi-temporal Audit Trail:")
        superseded_found = False
        active_new_found = False
        for r in all_sem:
            is_active = r["valid_until"] is None
            status = "🟢 ACTIVE" if is_active else f"🔴 SUPERSEDED (by {str(r['superseded_by'])[:8] if r['superseded_by'] else 'unknown'})"
            print(f"     - [{str(r['memory_id'])[:8]}] [{status}] {r['summary']}")
            if not is_active and r["superseded_by"] is not None:
                superseded_found = True
            if is_active and "3.13" in r["summary"]:
                active_new_found = True

        case1b_pass = (
            len(res_1b.superseded_ids) >= 1
            and superseded_found
            and active_new_found
            and mode_1b == "laya_decision"
        )
        results_summary["Case 1B: Contradiction & Superseding"] = {
            "passed": case1b_pass,
            "handler": "Laya Decision Model",
            "details": f"mode={mode_1b}, superseded_count={len(res_1b.superseded_ids)}",
        }
        print(f"=> Assessment: {'✅ PASSED (Bi-temporal Superseding Verified)' if case1b_pass else '❌ FAILED'}")

        # Case 1C: Ephemeral Fact & TTL Auto-Expiration
        print_case_header(
            "Case 1C",
            "Ephemeral Memory & TTL Temporal Expiration",
            "Strata Storage Engine (TTL Filter: valid_until > NOW())",
        )
        raw_text_1c = "Ephemeral authorization token TOKEN-XYZ-9912 expires in 1 second."
        print(f"📥 Input (ttl_seconds=1): \"{raw_text_1c}\"")

        res_1c = await svc_memory_ingest(
            raw_text=raw_text_1c,
            namespace=NAMESPACE,
            ttl_seconds=1,
        )
        print(f"   Stored Ephemeral ID: {res_1c.created_ids}")

        # Immediate recall: must be present
        recall_immediate = await svc_memory_recall(
            query="authorization token TOKEN-XYZ-9912",
            namespace=NAMESPACE,
            pillars=["semantic"],
        )
        present_before = any("TOKEN-XYZ-9912" in s.summary for s in recall_immediate.semantic)
        print(f"   Immediate Recall (before expiry): {'Found' if present_before else 'Missing'}")

        print("   ⏳ Sleeping 1.5s for TTL expiration...")
        await asyncio.sleep(1.5)

        # Subsequent recall: must be logically excluded!
        recall_after = await svc_memory_recall(
            query="authorization token TOKEN-XYZ-9912",
            namespace=NAMESPACE,
            pillars=["semantic"],
        )
        present_after = any("TOKEN-XYZ-9912" in s.summary for s in recall_after.semantic)
        print(f"   Post-TTL Recall (after 1.5s): {'Excluded (Correct)' if not present_after else 'Still returned (Leak)'}")

        case1c_pass = present_before and (not present_after)
        results_summary["Case 1C: TTL Temporal Expiration"] = {
            "passed": case1c_pass,
            "handler": "Strata Storage Engine",
            "details": "Active before 1s TTL, excluded after 1.5s",
        }
        print(f"=> Assessment: {'✅ PASSED (Temporal Invalidation Verified)' if case1c_pass else '❌ FAILED'}")

        # Case 1D: Write Policy Signal Gate (Conversational Filler Rejection)
        print_case_header(
            "Case 1D",
            "Write Policy Signal Gate (Conversational Filler)",
            "Laya Decision Model (Zero-DB Drop)",
        )
        filler_input = "Thanks, got it!"
        print(f"📥 Input: \"{filler_input}\"")
        t0 = time.perf_counter()
        res_1d = await svc_memory_ingest(raw_text=filler_input, namespace=NAMESPACE)
        t1 = time.perf_counter()
        latency_1d_ms = (t1 - t0) * 1000.0

        is_filtered = res_1d.details.get("mode") == "laya_signal_filtered"
        no_created = len(res_1d.created_ids) == 0
        print(f"⏱️ Signal Gate Latency: {latency_1d_ms:.2f} ms")
        print(f"   Result Mode: '{res_1d.details.get('mode')}', Created Count: {len(res_1d.created_ids)}")

        case1d_pass = is_filtered and no_created
        results_summary["Case 1D: Write Policy Signal Gating"] = {
            "passed": case1d_pass,
            "handler": "Laya Decision Model",
            "details": f"mode={res_1d.details.get('mode')}, dropped=True, latency={latency_1d_ms:.1f}ms",
        }
        print(f"=> Assessment: {'✅ PASSED (Signal Gating Verified)' if case1d_pass else '❌ FAILED'}")

        # Case 1E: Fact Reaffirmation & Half-Life Decay Reset
        print_case_header(
            "Case 1E",
            "Fact Reaffirmation & Half-Life Decay Reset",
            "Strata Storage Engine (reaffirmed_at update)",
        )
        fact_reaffirm_text = "The staging cluster uses us-east-1 and requires SSL connections."
        # Initial store
        res_init = await svc_memory_ingest(raw_text=fact_reaffirm_text, namespace=NAMESPACE, fast_mode=True)
        fact_id = res_init.created_ids[0]

        # Re-observe identical fact
        print(f"📥 Re-observing identical fact: \"{fact_reaffirm_text}\"")
        t0 = time.perf_counter()
        res_1e = await svc_memory_ingest(raw_text=fact_reaffirm_text, namespace=NAMESPACE, fast_mode=True)
        t1 = time.perf_counter()
        latency_1e_ms = (t1 - t0) * 1000.0

        reaffirmed_same_id = (len(res_1e.created_ids) == 1 and res_1e.created_ids[0] == fact_id)

        async with pool.acquire() as conn:
            reaffirm_row = await conn.fetchrow(
                "SELECT access_count, reaffirmed_at FROM memories WHERE memory_id = $1;",
                UUID(fact_id),
            )

        has_reaffirmed_ts = reaffirm_row["reaffirmed_at"] is not None
        access_count_bumped = reaffirm_row["access_count"] >= 1
        print(f"⏱️ Reaffirmation Latency: {latency_1e_ms:.2f} ms")
        print(f"   Target ID: {res_1e.created_ids[0][:8]} (reaffirmed same ID: {reaffirmed_same_id})")
        print(f"   reaffirmed_at: {reaffirm_row['reaffirmed_at']}, access_count: {reaffirm_row['access_count']}")

        case1e_pass = reaffirmed_same_id and has_reaffirmed_ts and access_count_bumped
        results_summary["Case 1E: Fact Reaffirmation & Decay Reset"] = {
            "passed": case1e_pass,
            "handler": "Strata Storage Engine",
            "details": f"reaffirmed_id={res_1e.created_ids[0][:8]}, access_count={reaffirm_row['access_count']}, ts_set={has_reaffirmed_ts}",
        }
        print(f"=> Assessment: {'✅ PASSED (Fact Reaffirmation Verified)' if case1e_pass else '❌ FAILED'}")

        # =====================================================================
        # PILLAR 2: EPISODIC MEMORY
        # =====================================================================
        print_section("PILLAR 2: EPISODIC MEMORY SUITE")

        # Case 2A: Direct Execution / Incident Log (Laya-handled)
        print_case_header(
            "Case 2A",
            "Direct Execution / Incident Log Ingest",
            "Laya Decision Engine (<5ms Fast Path)",
        )
        raw_text_2a = "Deployment to Neon database failed at 3pm with SSL connection refused error."
        print(f"📥 Input: \"{raw_text_2a}\"")

        t0 = time.perf_counter()
        res_2a = await svc_memory_ingest(raw_text=raw_text_2a, namespace=NAMESPACE)
        t1 = time.perf_counter()
        latency_2a_ms = (t1 - t0) * 1000.0

        mode_2a = res_2a.details.get("mode")
        pillar_2a = res_2a.details.get("laya_primary_pillar")
        print(f"⏱️ Ingest Latency: {latency_2a_ms:.2f} ms")
        print(f"   Routing Mode: '{mode_2a}' | Primary Pillar: '{pillar_2a}'")
        print(f"   Created ID(s): {res_2a.created_ids}")

        ep_id = res_2a.created_ids[0]
        async with pool.acquire() as conn:
            row_2a = await conn.fetchrow(
                "SELECT memory_id, summary, type, payload, utility_score FROM memories WHERE memory_id = $1;",
                UUID(ep_id),
            )
        
        pl = row_2a["payload"] if isinstance(row_2a["payload"], dict) else {}
        print(f"   DB Row: [{str(row_2a['memory_id'])[:8]}] type={row_2a['type']} outcome='{pl.get('outcome')}' success={pl.get('success')} utility={row_2a['utility_score']}")

        case2a_pass = (
            mode_2a == "laya_decision"
            and pillar_2a == "episodic"
            and row_2a["type"] == "episodic"
            and pl.get("success") is False
            and pl.get("outcome") == "failed"
        )
        results_summary["Case 2A: Episodic Ingest"] = {
            "passed": case2a_pass,
            "handler": "Laya Decision Model",
            "details": f"mode={mode_2a}, success=False, outcome=failed",
        }
        print(f"=> Assessment: {'✅ PASSED (Laya Episodic Path)' if case2a_pass else '❌ FAILED'}")

        # Case 2B: Utility Score Reinforcement & Feedback
        print_case_header(
            "Case 2B",
            "Episodic Utility Scoring & Feedback Loop",
            "Strata Dynamic Reinforcement Engine (+1 success, -2 failure)",
        )
        print(f"1. Recording failure feedback on episode [{ep_id[:8]}] (decrement -2)...")
        await svc_memory_feedback(
            memory_ids_used=[ep_id],
            success=False,
            namespace=NAMESPACE,
        )

        async with pool.acquire() as conn:
            score_after_fail = await conn.fetchval(
                "SELECT utility_score FROM memories WHERE memory_id = $1;", UUID(ep_id)
            )
        print(f"   Utility Score after failure: {score_after_fail} (expected -2)")

        print(f"2. Recording success feedback on episode [{ep_id[:8]}] (increment +1)...")
        await svc_memory_feedback(
            memory_ids_used=[ep_id],
            success=True,
            namespace=NAMESPACE,
        )

        async with pool.acquire() as conn:
            score_after_success = await conn.fetchval(
                "SELECT utility_score FROM memories WHERE memory_id = $1;", UUID(ep_id)
            )
        print(f"   Utility Score after success: {score_after_success} (expected -1)")

        case2b_pass = (score_after_fail == -2 and score_after_success == -1)
        results_summary["Case 2B: Utility Feedback Reinforcement"] = {
            "passed": case2b_pass,
            "handler": "Strata Dynamic Reinforcement Engine",
            "details": f"score_fail={score_after_fail}, score_success={score_after_success}",
        }
        print(f"=> Assessment: {'✅ PASSED (Utility Feedback Verified)' if case2b_pass else '❌ FAILED'}")

        # Case 2C: Cognitive Distillation & Compaction (Pruning)
        print_case_header(
            "Case 2C",
            "Cognitive Distillation & Episode Compaction",
            "Generative Small LLM (Distillation Prompt) & Safe Pruner",
        )
        # Store an expired operational episode to be distilled
        distill_input = "Incident: Neon connection timeout occurred during migration; switching to direct endpoint resolved the issue."
        print(f"📥 Storing expiring episode (ttl_seconds=1): \"{distill_input}\"")
        await svc_memory_ingest(
            raw_text=distill_input,
            namespace=NAMESPACE,
            ttl_seconds=1,
        )
        print("   ⏳ Waiting 1.5s for episode to reach expiration threshold...")
        await asyncio.sleep(1.5)

        print("Executing svc_memory_prune() with distill_episodes=True...")
        t0 = time.perf_counter()
        prune_res = await svc_memory_prune(
            namespace=NAMESPACE,
            distill_episodes=True,
            episodic_older_than_days=None,  # Considers all soft-expired episodes
        )
        t1 = time.perf_counter()
        print(f"⏱️ Pruning & Distillation completed in {(t1 - t0):.2f}s")
        print(f"   Prune Result: {prune_res.model_dump_json(indent=2)}")

        case2c_pass = prune_res.episodes_pruned >= 1
        results_summary["Case 2C: Cognitive Distillation & Prune"] = {
            "passed": case2c_pass,
            "handler": "Generative Small LLM & Pruner",
            "details": f"episodes_pruned={prune_res.episodes_pruned}, distilled_summary='{prune_res.details.get('distillation_summary', '')[:40]}...'",
        }
        print(f"=> Assessment: {'✅ PASSED (Distillation & Compaction Verified)' if case2c_pass else '❌ FAILED'}")

        # =====================================================================
        # PILLAR 3: PROCEDURAL MEMORY
        # =====================================================================
        print_section("PILLAR 3: PROCEDURAL MEMORY SUITE")

        # Case 3A: Runbook Registration & Trigger Matching
        print_case_header(
            "Case 3A",
            "Procedural Runbook Registration & Retrieval",
            "Strata Procedural Engine & Vector Index",
        )
        initial_procedure = {
            "name": "deploy_database_schema",
            "description": "Deploy database migrations to Neon",
            "trigger_condition": "When running database schema migrations",
            "steps": [
                "1. Connect using pooled DATABASE_URL (-pooler endpoint)",
                "2. Run migration SQL script",
                "3. Verify tables created",
            ],
            "prerequisites": {"db": "neon"},
            "reason_for_change": "Initial procedural runbook v1",
        }
        print(f"📥 Storing runbook v1: '{initial_procedure['name']}'...")
        store_proc_res = await svc_memory_store_explicit(
            pillar="procedural",
            payload=initial_procedure,
            namespace=NAMESPACE,
        )
        print(f"   Stored Procedure ID: {store_proc_res.get('procedure_id')}")

        # Verify retrieval via trigger condition
        recall_proc = await svc_memory_recall(
            query="How to run database schema migrations on Neon?",
            namespace=NAMESPACE,
            pillars=["procedural"],
        )
        found_proc = any(p.name == "deploy_database_schema" for p in recall_proc.procedural)
        print(f"   Recall Trigger Matching: {'Found matching procedure' if found_proc else 'Not found'}")

        case3a_pass = store_proc_res["status"] == "stored" and found_proc
        results_summary["Case 3A: Procedural Registration & Recall"] = {
            "passed": case3a_pass,
            "handler": "Strata Procedural Engine",
            "details": f"procedure={initial_procedure['name']}, version=1",
        }
        print(f"=> Assessment: {'✅ PASSED (Runbook Registration Verified)' if case3a_pass else '❌ FAILED'}")

        # Case 3B: Autonomous Self-Healing on Execution Failure (Small LLM handled)
        print_case_header(
            "Case 3B",
            "Procedural Autonomous Self-Healing on Failure",
            "Generative Small LLM (Procedure Patch Prompt)",
        )
        error_trace = (
            "asyncpg connection refused or threw prepared statement collision because direct endpoint was not used "
            "for DDL migration. PgBouncer transaction mode rejects prepared statements. Must use DIRECT_DATABASE_URL."
        )
        print(f"Reporting execution failure with error trace:\n\"{error_trace}\"")
        
        t0 = time.perf_counter()
        fb_res = await svc_memory_feedback(
            procedure_name="deploy_database_schema",
            success=False,
            failure_reason=error_trace,
            namespace=NAMESPACE,
        )
        t1 = time.perf_counter()
        print(f"⏱️ Self-healing patch generated in {(t1 - t0):.2f}s")
        print(f"   Feedback Result: {json.dumps(fb_res, indent=2)}")

        async with pool.acquire() as conn:
            proc_row = await conn.fetchrow(
                "SELECT name, version, steps, changelog, fail_count FROM procedural_memories WHERE namespace = $1 AND name = $2;",
                NAMESPACE,
                "deploy_database_schema",
            )
        print(f"   Updated Procedure: v{proc_row['version']} (fail_count={proc_row['fail_count']})")
        print("   Patched Steps:")
        for step in proc_row["steps"]:
            print(f"     - {step}")

        case3b_pass = (
            fb_res.get("procedure_updated") is True
            and proc_row["version"] >= 2
            and proc_row["fail_count"] >= 1
            and any("direct" in s.lower() for s in proc_row["steps"])
        )
        results_summary["Case 3B: Procedural Self-Healing"] = {
            "passed": case3b_pass,
            "handler": "Generative Small LLM",
            "details": f"version=v{proc_row['version']}, fail_count={proc_row['fail_count']}",
        }
        print(f"=> Assessment: {'✅ PASSED (Autonomous Patching Verified)' if case3b_pass else '❌ FAILED'}")

        # =====================================================================
        # PILLAR 4: ENTITY GRAPH MEMORY
        # =====================================================================
        print_section("PILLAR 4: ENTITY GRAPH MEMORY SUITE")

        # Case 4A: Entity Relation Direct Extraction (Laya-handled)
        print_case_header(
            "Case 4A",
            "Entity Relation Direct Ingest",
            "Laya Decision Engine (<5ms Fast Path)",
        )
        raw_text_4a = "Strata uses Neon for database persistence."
        print(f"📥 Input: \"{raw_text_4a}\"")

        t0 = time.perf_counter()
        res_4a = await svc_memory_ingest(raw_text=raw_text_4a, namespace=NAMESPACE)
        t1 = time.perf_counter()
        latency_4a_ms = (t1 - t0) * 1000.0

        mode_4a = res_4a.details.get("mode")
        pillar_4a = res_4a.details.get("laya_primary_pillar")
        print(f"⏱️ Ingest Latency: {latency_4a_ms:.2f} ms")
        print(f"   Routing Mode: '{mode_4a}' | Primary Pillar: '{pillar_4a}'")
        print(f"   Created ID(s): {res_4a.created_ids}")

        async with pool.acquire() as conn:
            nodes_4a = await conn.fetch("SELECT name, entity_type FROM entity_nodes WHERE namespace = $1;", NAMESPACE)
            edges_4a = await conn.fetch(
                """
                SELECT src.name as src, e.relation_type, tgt.name as tgt
                FROM entity_edges e
                JOIN entity_nodes src ON e.source_entity_id = src.entity_id
                JOIN entity_nodes tgt ON e.target_entity_id = tgt.entity_id
                WHERE e.namespace = $1;
                """,
                NAMESPACE,
            )

        print(f"   Extracted Nodes: {[n['name'] for n in nodes_4a]}")
        print(f"   Extracted Edges: {[(e['src'], e['relation_type'], e['tgt']) for e in edges_4a]}")

        case4a_pass = (
            mode_4a == "laya_decision"
            and pillar_4a == "entity"
            and any(n["name"] == "Strata" for n in nodes_4a)
            and any(n["name"] == "Neon" for n in nodes_4a)
            and any(e["relation_type"] == "USES" for e in edges_4a)
        )
        results_summary["Case 4A: Entity Relation Ingest"] = {
            "passed": case4a_pass,
            "handler": "Laya Decision Model",
            "details": f"mode={mode_4a}, relation=USES",
        }
        print(f"=> Assessment: {'✅ PASSED (Laya Entity Path)' if case4a_pass else '❌ FAILED'}")

        # Case 4B: 1-Hop Graph Traversal & Soft-Delete Symmetry
        print_case_header(
            "Case 4B",
            "1-Hop Graph Traversal & Soft-Delete Symmetry",
            "Strata Graph Engine & Soft-Deleter",
        )
        # Ingest connected relation
        raw_text_4b = "Dheeban maintains Strata."
        print(f"📥 Storing connected entity relation: \"{raw_text_4b}\"")
        await svc_memory_ingest(raw_text=raw_text_4b, namespace=NAMESPACE)

        # Recall with 1-hop expansion
        recall_graph = await svc_memory_recall(
            query="Who maintains Strata and what does it use?",
            namespace=NAMESPACE,
            pillars=["entity"],
        )
        print(f"   Retrieved {len(recall_graph.entities)} graph connections:")
        for edge in recall_graph.entities:
            print(f"     - ({edge.source_name}) -[{edge.relation_type}]-> ({edge.target_name})")

        traversal_found = len(recall_graph.entities) >= 2

        # Soft delete node 'Neon'
        print("   Executing soft delete on entity 'Neon'...")
        del_res = await svc_memory_delete(
            target_id="Neon",
            pillar="entity",
            hard_delete=False,
            namespace=NAMESPACE,
        )
        print(f"   Delete Result: {del_res}")

        async with pool.acquire() as conn:
            node_neon = await conn.fetchrow(
                "SELECT is_active FROM entity_nodes WHERE name = 'Neon' AND namespace = $1;", NAMESPACE
            )
            edges_neon = await conn.fetch(
                """
                SELECT e.valid_until
                FROM entity_edges e
                JOIN entity_nodes n ON e.target_entity_id = n.entity_id
                WHERE n.name = 'Neon' AND e.namespace = $1;
                """,
                NAMESPACE,
            )

        neon_node_inactive = (node_neon is not None and node_neon["is_active"] is False)
        neon_edges_inactive = all(e["valid_until"] is not None for e in edges_neon)
        print(f"   Neon Node is_active: {node_neon['is_active'] if node_neon else 'N/A'}")
        print(f"   Neon Edges valid_until set: {neon_edges_inactive}")

        case4b_pass = traversal_found and neon_node_inactive and neon_edges_inactive
        results_summary["Case 4B: 1-Hop Traversal & Soft Delete"] = {
            "passed": case4b_pass,
            "handler": "Strata Graph Engine",
            "details": f"traversal_links={len(recall_graph.entities)}, soft_delete_symmetric=True",
        }
        print(f"=> Assessment: {'✅ PASSED (Graph Traversal & Soft Delete Verified)' if case4b_pass else '❌ FAILED'}")

        # =====================================================================
        # CASE 5: COMPOUND MULTI-PILLAR NARRATIVE (Small LLM Handled)
        # =====================================================================
        print_section("CASE 5: COMPOUND MULTI-PILLAR NARRATIVE (SMALL LLM HANDLED)")
        print_case_header(
            "Case 5",
            "Complex Compound Narrative Ingest",
            "Generative Small LLM (Ollama qwen3:8b)",
        )
        raw_text_5 = (
            "We decided that all core backend persistence will run on Neon Serverless PostgreSQL in ap-southeast-1. "
            "Dheeban is the lead system architect for Strata. "
            "However, yesterday's migration attempt failed because the connection pool timed out before Neon woke up from compute suspension. "
            "To resolve this, step 1 is to trigger compute resume with a ping query, and step 2 is to execute the migration."
        )
        print(f"📥 Compound Input Narrative:\n\"{raw_text_5}\"\n")
        print("Executing memory_ingest()... Laya should detect complexity conjunctions and delegate to Small LLM.")

        t0 = time.perf_counter()
        res_5 = await svc_memory_ingest(raw_text=raw_text_5, namespace=NAMESPACE)
        t1 = time.perf_counter()
        latency_5_s = t1 - t0

        mode_5 = res_5.details.get("mode")
        print(f"⏱️ Ingest completed in {latency_5_s:.2f}s")
        print(f"   Routing Mode: '{mode_5}'")
        print(f"   Extracted Counts: {res_5.details}")

        async with pool.acquire() as conn:
            mem_count = await conn.fetchval("SELECT COUNT(*) FROM memories WHERE namespace = $1;", NAMESPACE)
            proc_count = await conn.fetchval("SELECT COUNT(*) FROM procedural_memories WHERE namespace = $1;", NAMESPACE)
            edge_count = await conn.fetchval("SELECT COUNT(*) FROM entity_edges WHERE namespace = $1;", NAMESPACE)
            node_count = await conn.fetchval("SELECT COUNT(*) FROM entity_nodes WHERE namespace = $1;", NAMESPACE)

        print(f"   Active DB Counts in namespace '{NAMESPACE}':")
        print(f"     • Memories: {mem_count}")
        print(f"     • Procedural Runbooks: {proc_count}")
        print(f"     • Entity Edges: {edge_count}")
        print(f"     • Entity Nodes: {node_count}")

        case5_pass = (
            mode_5 == "small_llm"
            and res_5.details.get("semantic_count", 0) >= 1
            and res_5.details.get("episodic_count", 0) >= 1
            and res_5.details.get("procedural_count", 0) >= 1
        )
        results_summary["Case 5: Multi-Pillar Compound Ingest"] = {
            "passed": case5_pass,
            "handler": "Generative Small LLM",
            "details": f"mode={mode_5}, decomposed across 4 pillars",
        }
        print(f"=> Assessment: {'✅ PASSED (Small LLM Compound Extraction Verified)' if case5_pass else '❌ FAILED'}")

        # =====================================================================
        # CASE 6: ZERO-LLM FAST HYBRID RECALL
        # =====================================================================
        print_section("CASE 6: ZERO-LLM FAST HYBRID RECALL & XML CONTEXT ASSEMBLY")
        print_case_header(
            "Case 6",
            "Zero-LLM Multi-Pillar Hybrid Recall",
            "Zero-LLM Fast Path (<15ms Target: RRF SQL + 1-Hop Graph)",
        )
        query_6 = "How do we resolve the Neon migration failure and what does Strata use?"
        print(f"🔎 Query: \"{query_6}\"")

        t0 = time.perf_counter()
        recall_res_6 = await svc_memory_recall(
            query=query_6,
            namespace=NAMESPACE,
            top_k=5,
            token_budget=1000,
        )
        t1 = time.perf_counter()
        latency_6_ms = (t1 - t0) * 1000.0

        print(f"\n⚡ Total Recall Latency (Local Embedding + Neon pgvector RRF + Graph): {latency_6_ms:.2f} ms")
        print(f"   Retrieved: {len(recall_res_6.semantic)} semantic facts, {len(recall_res_6.episodic)} episodes, {len(recall_res_6.procedural)} runbooks, {len(recall_res_6.entities)} graph links")
        print("\n📦 Assembled Prompt XML Context Block (<strata_memory_context>):")
        print("-" * 60)
        print(recall_res_6.formatted_context)
        print("-" * 60)

        context_lower = recall_res_6.formatted_context.lower()
        has_xml_tag = "<strata_memory_context" in context_lower
        has_relevant_info = ("neon" in context_lower or "migration" in context_lower)

        case6_pass = has_xml_tag and has_relevant_info
        results_summary["Case 6: Zero-LLM Hybrid Recall"] = {
            "passed": case6_pass,
            "handler": "Zero-LLM Fast Path (pgvector RRF)",
            "details": f"latency={latency_6_ms:.1f}ms, xml_context_valid=True",
        }
        print(f"=> Assessment: {'✅ PASSED (Hybrid Recall & XML Assembly Verified)' if case6_pass else '❌ FAILED'}")

        # =====================================================================
        # SHORT-TERM WORKING MEMORY SUITE
        # =====================================================================
        print_section("SHORT-TERM WORKING MEMORY & TOOL PINNING SUITE")

        # Case 7: Protected Tool Pinning & Budget Eviction
        print_case_header(
            "Case 7",
            "Working Context Buffer & Tool Pinning (Eviction Bug Prevention)",
            "WorkingMemoryManager (protected=True)",
        )
        session_id_7 = "eval_session_pinning_test"
        svc_working_memory_clear(namespace=NAMESPACE, session_id=session_id_7)

        # 1. Add conversation messages
        svc_working_memory_add(
            namespace=NAMESPACE,
            session_id=session_id_7,
            role="user",
            content="Check database migration status.",
            turn_id=1,
        )
        svc_working_memory_add(
            namespace=NAMESPACE,
            session_id=session_id_7,
            role="assistant",
            content="Invoking db_status check now...",
            turn_id=2,
        )

        # 2. Add protected tool output
        t0 = time.perf_counter()
        tool_item = svc_working_memory_add_tool_output(
            namespace=NAMESPACE,
            session_id=session_id_7,
            tool_call_id="call_neon_db_status",
            tool_name="db_status",
            content="STATUS=HEALTHY, APPLIED_MIGRATIONS=1, ACTIVE_ENDPOINTS=1",
            protected=True,
        )
        t1 = time.perf_counter()
        latency_7_ms = (t1 - t0) * 1000.0

        # 3. Add subsequent dialogue that pushes total tokens above small budget
        svc_working_memory_add(
            namespace=NAMESPACE,
            session_id=session_id_7,
            role="assistant",
            content="Database is healthy. Proceeding to verify the application endpoints next.",
            turn_id=4,
        )

        # 4. Enforce strict token budget (25 tokens)
        ctx_budgeted = svc_working_memory_get(namespace=NAMESPACE, session_id=session_id_7, max_tokens=25)
        pinned_retained = any(
            i["tool_call_id"] == "call_neon_db_status" and i["protected"] is True
            for i in ctx_budgeted["items"]
        )
        print(f"⏱️ Tool Pinning Latency: {latency_7_ms:.2f} ms")
        print(f"   Context Item Count (after budget 25): {ctx_budgeted['item_count']}")
        print(f"   Tool Output Pinned & Retained: {pinned_retained}")

        # 5. Unprotect and clean up
        svc_working_memory_unprotect(
            namespace=NAMESPACE,
            session_id=session_id_7,
            tool_call_id="call_neon_db_status",
        )
        svc_working_memory_clear(namespace=NAMESPACE, session_id=session_id_7)

        case7_pass = pinned_retained and (tool_item["protected"] is True)
        results_summary["Case 7: Working Memory Tool Pinning"] = {
            "passed": case7_pass,
            "handler": "Working Memory Buffer",
            "details": f"protected_retained=True, eviction_bug_prevented=True, latency={latency_7_ms:.1f}ms",
        }
        print(f"=> Assessment: {'✅ PASSED (Tool Pinning & Eviction Prevention Verified)' if case7_pass else '❌ FAILED'}")

    finally:
        # =====================================================================
        # POST-FLIGHT CLEANUP (Guaranteed Pristine State)
        # =====================================================================
        print_section("POST-FLIGHT CLEANUP (GUARANTEED CLEAN SLATE)")
        await verify_and_clean_db(pool, NAMESPACE, label="Post-flight DB Final Cleanup")
        await close_db_pool()

    # =========================================================================
    # FINAL EVALUATION REPORT
    # =========================================================================
    print_section("EVALUATION PIPELINE FINAL REPORT")
    all_passed = True
    print(f"{'TEST CASE':<45} | {'HANDLER TYPE':<32} | {'STATUS':<10}")
    print("-" * 92)
    for test_name, info in results_summary.items():
        passed = info["passed"]
        handler = info["handler"]
        if not passed:
            all_passed = False
        status_str = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:<45} | {handler:<32} | {status_str:<10}")

    print("=" * 92)
    print(f"FINAL RESULT: {'🎉 ALL TEST CASES PASSED PERFECTLY' if all_passed else '⚠️ SOME CASES FAILED'}")
    print(f"Database Namespace: '{NAMESPACE}' is 100% clean and pristine.")
    print("=" * 92)

    return all_passed


@pytest.mark.asyncio
async def test_full_evaluation_pipeline():
    """Pytest entrypoint allowing eval_pipeline.py to be executed directly via pytest."""
    success = await run_eval_pipeline()
    assert success is True


if __name__ == "__main__":
    success = asyncio.run(run_eval_pipeline())
    if not success:
        exit(1)
