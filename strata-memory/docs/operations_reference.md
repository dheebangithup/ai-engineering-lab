# Strata Memory Engine: Operations, Options & Filters Reference

This document provides a comprehensive technical reference for **all 6 core operations**, their input parameters, optional filters, data contracts, internal algorithms, and payload schemas across the **4 Memory Pillars**.

---

## 🏛️ Summary Matrix of Operations

| Operation Name | FastMCP Tool | REST API Route | Primary Function | LLM Involved? | Latency Target |
|---|---|---|---|---|---|
| **`memory_ingest`** | `memory_ingest` | `POST /v1/memory/ingest` | Autonomous routing & extraction across 4 pillars | Yes (Small LLM) or Fallback | ~1.5s–3s (LLM) / <15ms (Fast) |
| **`memory_recall`** | `memory_recall` | `POST /v1/memory/recall` | Deterministic hybrid RRF retrieval & XML context packing | **No (Zero-LLM)** | **<15ms** |
| **`memory_store_explicit`** | `memory_store_explicit` | `POST /v1/memory/store` | Direct, structured insertion into any pillar | **No (Zero-LLM)** | <10ms |
| **`memory_edit`** | `memory_edit` | `POST /v1/memory/edit` | Natural language modification & superseding | Yes (Small LLM) | ~1.5s |
| **`memory_feedback`** | `memory_feedback` | `POST /v1/memory/feedback` | Utility score reinforcement & skill self-healing | Optional (Only on fail patch) | <10ms / ~1.5s (if patching) |
| **`memory_delete`** | `memory_delete` | `POST /v1/memory/delete` | Soft-invalidation or hard deletion | **No (Zero-LLM)** | <10ms |

---

## 1. `memory_recall` (Read Path: Hybrid Search & Context Packing)

Deterministic, multi-pillar recall engine that fuses vector cosine similarity, full-text search (BM25), Bayesian procedural ranking, and entity property graph traversal in a **single round-trip**.

### Parameters & Option Filters

| Parameter | Type | Required? | Default | Description & Filters |
|---|---|---|---|---|
| `query` | `string` | **Yes** | — | Search query text used for both FastEmbed embedding and Postgres `websearch_to_tsquery`. |
| `namespace` | `string` | No | `"default"` | Multi-tenancy filter. Constrains search to memories within this isolated namespace. |
| `pillars` | `List[string]` | No | `["semantic", "episodic", "procedural", "entity"]` | **Pillar Filter.** Restricts recall to any combination of: `"semantic"`, `"episodic"`, `"procedural"`, `"entity"`. |
| `top_k` | `integer` | No | `5` | Maximum number of candidate items returned per pillar. |
| `token_budget` | `integer` | No | `1500` | Maximum token budget for the generated `<strata_memory_context>` XML block (computed as `chars // 4`). Truncation preserves XML tag validity. |

### Internal Ranking & Filtering Logic

1. **Semantic & Episodic Ranking (Reciprocal Rank Fusion - RRF):**
   ```sql
   Score = (1.0 / (60.0 + rank_vector)) + (1.0 / (60.0 + rank_bm25)) + (utility_boost)
   ```
   - `rank_vector`: Derived from HNSW cosine distance `(m.embedding <=> query_vec)`. Match threshold: `similarity >= 0.35`.
   - `rank_bm25`: Derived from `ts_rank_cd(to_tsvector('english', summary), websearch_to_tsquery('english', query))`.
   - `utility_boost`: `LEAST(GREATEST(utility_score, -5), 20) * 0.001` (Memories proven useful gain higher rank).
   - Filter: `valid_until IS NULL` (only active facts are returned; superseded facts are omitted).
2. **Procedural Ranking (Bayesian Skill Scoring):**
   ```text
   Score = 0.75 * (1.0 - CosineDistance) + 0.25 * ((success_count + 1) / (success_count + fail_count + 2))
   ```
   - Uses Laplace smoothing: Untested skills start at 50% success probability ($1/2 = 0.5$).
   - Filter: `is_active = TRUE`.
3. **Entity Subgraph Traversal:**
   - Vector similarity or `name ILIKE '%query%'` finds seed nodes.
   - 1-hop traversal across `entity_edges` where `valid_until IS NULL`.

### Example Payload
```json
{
  "query": "How do we deploy database migrations on Neon?",
  "namespace": "production",
  "pillars": ["semantic", "procedural", "entity"],
  "top_k": 3,
  "token_budget": 800
}
```

### Response Schema
```json
{
  "namespace": "production",
  "query": "How do we deploy database migrations on Neon?",
  "semantic": [
    {
      "memory_id": "9158729e-356d-4998-b74e-30a44a4b8a65",
      "summary": "User prefers Neon PostgreSQL with pgvector.",
      "payload": {},
      "tags": ["neon", "database"],
      "utility_score": 1,
      "confidence": 1.0,
      "created_at": "2026-11-14T05:35:28.948255Z",
      "rrf_score": 0.0332
    }
  ],
  "episodic": [],
  "procedural": [
    {
      "procedure_id": "393040e7-0c98-42d6-b118-48fa50af0d77",
      "name": "neon_migration_runbook",
      "description": "How to execute DDL schema migrations against Neon",
      "trigger_condition": "When running database migrations",
      "steps": [
        "Ensure DIRECT_DATABASE_URL is used",
        "Execute 001_init_schema.sql with asyncpg",
        "Verify pgvector extension and HNSW indexes"
      ],
      "prerequisites": {"sslmode": "require"},
      "version": 1,
      "success_count": 1,
      "fail_count": 0,
      "success_rate": 0.666,
      "composite_score": 0.812
    }
  ],
  "entities": [
    {
      "edge_id": "b38a397c-cde2-47d2-ac94-e6d14c4b907a",
      "source_name": "Strata",
      "source_type": "software",
      "relation_type": "DEPLOYED_ON",
      "target_name": "Neon",
      "target_type": "cloud_service",
      "fact_summary": "Strata is deployed on Neon Serverless PostgreSQL",
      "properties": {},
      "valid_from": "2026-11-14T05:35:28.977283Z"
    }
  ],
  "formatted_context": "<strata_memory_context namespace=\"production\">\n  <semantic_facts>\n    - [mem_id=9158729e] User prefers Neon PostgreSQL with pgvector.\n  </semantic_facts>\n  <entity_graph>\n    - (Strata [software]) -[DEPLOYED_ON]-> (Neon [cloud_service]): Strata is deployed on Neon Serverless PostgreSQL\n  </entity_graph>\n  <procedural_skills>\n    - [skill=neon_migration_runbook v1 | success_rate=66%] Trigger: When running database migrations\n      Steps: 1. Ensure DIRECT_DATABASE_URL is used 2. Execute 001_init_schema.sql with asyncpg 3. Verify pgvector extension and HNSW indexes\n  </procedural_skills>\n</strata_memory_context>",
  "token_count_approx": 175
}
```

---

## 2. `memory_ingest` (Write Path: Autonomous Routing & Extraction)

Takes raw, unstructured text from an agent conversation or log, pre-fetches similar existing memories, and uses the Small Decision LLM (`qwen3:8b`) to split the text into 4 pillars, detect contradictions, and update knowledge.

### Parameters & Option Filters

| Parameter | Type | Required? | Default | Description & Filters |
|---|---|---|---|---|
| `raw_text` | `string` | **Yes** | — | Raw natural language input to be categorized and ingested. |
| `namespace` | `string` | No | `"default"` | Target namespace partition. |
| `fast_mode` | `boolean` | No | `false` | **Fast Mode Bypass.** If `true`, bypasses LLM extraction and immediately inserts `raw_text` as a semantic memory with `<15ms` latency. |
| `source_id` | `string` | No | `null` | Optional external reference ID (e.g., chat message ID, git commit hash, file path). |

### Response Schema
```json
{
  "success": true,
  "namespace": "production",
  "fast_mode": false,
  "created_ids": [
    "c8a14b1e-3f62-4e89-a212-61f6c4d7bb12",
    "f18b3174-8b6a-4933-bd88-0f0e309cb442"
  ],
  "superseded_ids": [
    "12a7629b-2c4f-4d92-a111-92b8d4f6c881"
  ],
  "details": {
    "semantic_count": 1,
    "episodic_count": 0,
    "procedural_count": 1,
    "entity_count": 1
  }
}
```

---

## 3. `memory_store_explicit` (Direct Structured Write)

Zero-LLM write path used when an agent or system already knows the exact pillar and structure of the data.

### Parameters

| Parameter | Type | Required? | Allowed Values |
|---|---|---|---|
| `pillar` | `string` | **Yes** | `"semantic"`, `"episodic"`, `"procedural"`, `"entity"` |
| `namespace` | `string` | No (default: `"default"`) | Multi-tenant namespace string |
| `payload` | `object` | **Yes** | Schema depends on `pillar` (see below) |

### Pillar-Specific Payload Schemas

#### A. Semantic Pillar (`pillar: "semantic"`)
Atomic facts, user configurations, preferences.
```json
{
  "pillar": "semantic",
  "namespace": "default",
  "payload": {
    "summary": "Agent runtime is Python 3.14 on macOS arm64.",
    "tags": ["runtime", "python", "macos"],
    "confidence": 1.0,
    "source_id": "session_config_v1",
    "supersede_memory_id": null,
    "payload": {"arch": "arm64", "python_version": "3.14.7"}
  }
}
```
*Filter/Supersede Rule:* If `supersede_memory_id` is passed, the target memory's `valid_until` is stamped with `NOW()`. If omitted, Strata auto-detects near-duplicate memories with cosine similarity `> 0.94` in the same namespace and supersedes them automatically.

#### B. Episodic Pillar (`pillar: "episodic"`)
Immutable execution history, situations, and results.
```json
{
  "pillar": "episodic",
  "namespace": "default",
  "payload": {
    "summary": "Applied 001_init_schema.sql to Neon database.",
    "situation": "Initial database bootstrap on fresh Neon compute",
    "action_taken": "Executed strata.db.run_migrations via direct connection",
    "outcome": "Success. Created 4 tables and HNSW vector indexes.",
    "success": true,
    "tags": ["migration", "ddl", "bootstrap"],
    "source_id": "deploy_job_104"
  }
}
```

#### C. Procedural Pillar (`pillar: "procedural"`)
Versioned workflows, skills, runbooks.
```json
{
  "pillar": "procedural",
  "namespace": "default",
  "payload": {
    "name": "deploy_neon_service",
    "description": "Step-by-step workflow for deploying to Neon",
    "trigger_condition": "When new database schema changes are merged",
    "steps": [
      "1. Verify DIRECT_DATABASE_URL has sslmode=require",
      "2. Run strata-migrate CLI",
      "3. Execute test suite against live database"
    ],
    "prerequisites": {
      "python": ">=3.11",
      "env_vars": ["DATABASE_URL", "DIRECT_DATABASE_URL"]
    },
    "reason_for_change": "Initial production runbook"
  }
}
```
*Versioning Rule:* If a procedure with `(namespace, name)` already exists, `version` is incremented (`version + 1`), and `{version, timestamp, reason}` is appended to `changelog`.

#### D. Entity Pillar (`pillar: "entity"`)
Bi-temporal property graph of nodes and edges.
```json
{
  "pillar": "entity",
  "namespace": "default",
  "payload": {
    "source_name": "StrataEngine",
    "source_type": "application",
    "source_summary": "4-pillar memory engine",
    "relation_type": "HOSTED_ON",
    "target_name": "Neon",
    "target_type": "infrastructure",
    "target_summary": "Serverless PostgreSQL with pgvector",
    "fact_summary": "StrataEngine is hosted on Neon serverless PostgreSQL",
    "invalidate_conflicting_relations": true,
    "properties": {
      "region": "ap-southeast-1",
      "provider": "aws"
    }
  }
}
```
*Invalidation Option:* When `invalidate_conflicting_relations = true`, any prior active edge with the same `(namespace, source, relation_type)` has `valid_until` set to `NOW()`.

---

## 4. `memory_edit` (Natural Language Modification)

Allows agents to modify or supersede an existing memory using natural language instructions.

### Parameters & Option Filters

| Parameter | Type | Required? | Description |
|---|---|---|---|
| `target_id_or_name` | `string` | **Yes** | Memory UUID (for Semantic/Episodic) or Procedure Name / Entity Name. |
| `instruction` | `string` | **Yes** | Natural language change (e.g., *"Update Neon region to ap-southeast-1"*). |
| `pillar` | `string` | No (default: `"semantic"`) | `"semantic"`, `"procedural"`, or `"entity"`. |
| `namespace` | `string` | No (default: `"default"`) | Multi-tenant namespace filter. |

### Behavior by Pillar
1. **Semantic:** Small LLM rewrites the fact to reflect the instruction. The old memory row is marked `valid_until = NOW()`, `superseded_by = <new_id>`, and the new revised fact is inserted.
2. **Procedural:** Small LLM modifies the step sequence based on the instruction. Procedure `version` is bumped and recorded in `changelog`.
3. **Entity:** Appends modification audit note to node summary or edge fact summary.

### Example Payload
```json
{
  "target_id_or_name": "9158729e-356d-4998-b74e-30a44a4b8a65",
  "instruction": "Change preferred vector dimensions from 1536 to 768 (FastEmbed).",
  "pillar": "semantic",
  "namespace": "production"
}
```

---

## 5. `memory_feedback` (Reinforcement Learning & Auto-Patching)

Closes the loop between memory recall and task execution.

### Parameters & Option Filters

| Parameter | Type | Required? | Default | Description |
|---|---|---|---|---|
| `memory_ids_used` | `List[string]` | No | `[]` | List of UUIDs of memories that assisted the agent. |
| `procedure_name` | `string` | No | `null` | Name of the procedure executed by the agent. |
| `success` | `boolean` | No | `true` | Whether the agent's task succeeded or failed. |
| `failure_reason` | `string` | No | `null` | Error trace or explanation of why the task failed. |
| `namespace` | `string` | No | `"default"` | Namespace partition. |

### Behavior & Scoring Rules

1. **Utility Score Updates:**
   - If `success == true`: `utility_score = utility_score + 1` for all `memory_ids_used`.
   - If `success == false`: `utility_score = utility_score - 2` for all `memory_ids_used`.
   - Clamped in RRF between `[-5, +20]`.
2. **Procedural Success/Failure Counter:**
   - If `success == true`: `success_count = success_count + 1`.
   - If `success == false`: `fail_count = fail_count + 1`.
3. **Automated Self-Healing / Runbook Patching:**
   - If `success == false` and `failure_reason` is supplied, the Small LLM inspects the failed procedure's existing `steps[]` and the `failure_reason`, generates a revised `steps[]` array, bumps the procedure `version = version + 1`, and logs the repair to `changelog`.

### Example Payload (Reporting a Failure with Auto-Patching)
```json
{
  "memory_ids_used": ["9158729e-356d-4998-b74e-30a44a4b8a65"],
  "procedure_name": "deploy_neon_service",
  "success": false,
  "failure_reason": "asyncpg threw prepared statement error because statement_cache_size was not 0 on Neon -pooler endpoint.",
  "namespace": "production"
}
```

---

## 6. `memory_delete` (Soft-Invalidation & Hard Deletion)

Controls memory pruning, expiration, and deletion.

### Parameters & Option Filters

| Parameter | Type | Required? | Default | Description |
|---|---|---|---|---|
| `target_id` | `string` | **Yes** | — | UUID of the memory item, or procedure/entity name. |
| `pillar` | `string` | No | `"semantic"` | `"semantic"`, `"episodic"`, `"procedural"`, or `"entity"`. |
| `hard_delete` | `boolean` | No | `false` | **Soft vs Hard Delete Filter.**<br>• If `false`: Soft invalidates (`valid_until = NOW()` or `is_active = FALSE`). Retains historical audit trail.<br>• If `true`: Executes `DELETE FROM ...`, permanently purging the row. |
| `namespace` | `string` | No | `"default"` | Multi-tenancy filter. |

### Example Payload
```json
{
  "target_id": "9158729e-356d-4998-b74e-30a44a4b8a65",
  "pillar": "semantic",
  "hard_delete": false,
  "namespace": "production"
}
```

---

## 8. Neon Compute Cost Optimization: Auto-Suspend Lifecycle

To eliminate idle compute spend on Neon Serverless PostgreSQL, Strata features an **automatic compute suspension trigger** executed in the `finally:` block of every MCP tool call and FastAPI request.

### Control Mechanism & Environment Variables

| Variable | Type | Default | Description |
|---|---|---|---|
| `NEON_KEEP_ALIVE` | `boolean` | `false` | **Compute Suspend Toggle**.<br>• `false` (default): Hits Neon API v2 `suspend` endpoint in the `finally:` block at the end of every call to save compute cost.<br>• `true`: Leaves the compute instance running. |
| `NEON_API_KEY` | `string` | `""` | Neon Management API key (`nkey_...`) from your Neon Console. |
| `NEON_PROJECT_ID` | `string` | `""` | (Optional) Neon Project ID. If omitted, Strata auto-discovers it via Neon API. |
| `NEON_ENDPOINT_ID` | `string` | `""` | (Optional) Compute endpoint ID. If omitted, Strata extracts it automatically from `DATABASE_URL` (e.g. `ep-divine-hill-a1p3fmik`). |

### Lifecycle Behavior:
1. When an agent calls any MCP tool (`memory_recall`, `memory_ingest`, etc.) or FastAPI endpoint (`/v1/memory/*`), the database operations run.
2. In the `finally:` block at the conclusion of the request:
   ```python
   try:
       # ... execute memory operation ...
   finally:
       await maybe_suspend_neon_compute()
   ```
3. If `NEON_KEEP_ALIVE=false` and `NEON_API_KEY` is present, Strata sends:
   ```http
   POST https://console.neon.tech/api/v2/projects/{project_id}/endpoints/{endpoint_id}/suspend
   Authorization: Bearer <NEON_API_KEY>
   ```
4. Neon immediately transitions the compute from `active` to `suspended`, stopping all billable compute seconds until the next call arrives.


Every table and query in Strata is partitioned by `namespace` (default: `"default"`).

- **Namespace Isolation:** Data stored in `namespace="team_alpha"` will **never** appear in recall queries for `namespace="team_beta"`.
- **Global Context:** To query across broad organizational knowledge, use a designated namespace such as `"global"` or `"org_shared"`.
- **Testing Namespaces:** You can spin up ephemeral namespaces (e.g., `namespace="test_run_42"`) for CI/CD runs and wipe them with zero risk to production memory strata.
