# Master System Specification: Strata — Standalone Autonomous 4-Pillar Memory Engine (Neon Postgres Edition)

## 1. Executive Summary & Project Identity

* **Project Name:** **Strata** (`strata-memory` / `strata-mcp`)
* **Core Concept:** Just as geological strata preserve layered history over time, **Strata** is a standalone, plug-and-play **4-Pillar Cognitive Memory Engine** backed by **Neon Serverless PostgreSQL (`pgvector` + `tsvector` + `JSONB`)**.
* **Universal Compatibility:** Any external agent, IDE, or framework (LangGraph, CrewAI, AutoGen, Hermes, Claude Desktop, Cursor, or custom harnesses) connects to Strata via **FastMCP (stdio/SSE)**, **FastAPI REST HTTP**, or **Python SDK**.

### Dual-Path Operational Architecture
1. **Deterministic, Ultra-Fast Read Path (<15ms, Zero-LLM):**
   When an external agent calls `memory_recall()`, Strata embeds the query locally via `FastEmbed` (`BAAI/bge-base-en-v1.5`, **768 dimensions**) and executes a single-round-trip SQL query on Neon Postgres combining **Reciprocal Rank Fusion (RRF)** (`pgvector` HNSW cosine similarity + `tsvector` full-text search), **Bayesian Procedural Skill ranking**, and **1-hop Entity Graph traversal**, packed neatly into the caller's token budget.
2. **Autonomous Memory-Side Intelligence on the Write Path (Option 1):**
   External agents do not need complex prompt engineering to classify or structure memories. When an agent calls `memory_ingest()` or `memory_edit()`, an internal **Small Decision LLM** (via Ollama, LM Studio, or any OpenAI-compatible endpoint, e.g., `qwen2.5:3b-instruct` or `llama3.2:3b`) inside Strata automatically extracts, categorizes, deduplicates, resolves contradictions, and routes data across the **4 Memory Pillars**:
   * **Semantic Layer:** Atomic facts, user preferences, and domain truths with bi-temporal validity (`valid_from`, `valid_until`, `superseded_by`).
   * **Episodic Layer:** Immutable timestamped execution traces, events, situations, actions, and outcomes.
   * **Procedural Layer:** Mutable, versioned step-by-step workflows, skills, and runbooks that self-evolve when failures occur.
   * **Entity Layer:** Bi-temporal property graph of people, projects, services, servers, and their active/historical relationships.

---

## 2. System Architecture Diagram

```
+-------------------------------------------------------------------------+
|        EXTERNAL CLIENTS (Any Agent, Harness, IDE, or Application)       |
|   (Connects via FastMCP stdio/SSE, FastAPI REST HTTP, or Python SDK)    |
+------------------------------------+------------------------------------+
                                     |
        +----------------------------+----------------------------+
        | WRITE PATH                                              | READ PATH
        | (`memory_ingest`, `memory_edit`,                        | (`memory_recall`,
        |  `memory_feedback`, `memory_delete`)                    |  `memory_get_graph`)
        v                                                         v
+------------------------------------+   +--------------------------------+
|   MEMORY-SIDE DECISION PROCESSOR   |   |  DETERMINISTIC RECALL ENGINE   |
|         (Small Local LLM)          |   |       (Zero-LLM, Fast)         |
| 1. Prefetches top similar memories |   | 1. Local FastEmbed (768-dim)   |
| 2. Splits raw text into 4 Pillars  |   | 2. SQL RRF (Vector + BM25 FTS) |
| 3. Detects & supersedes conflicts  |   | 3. Procedural Skill Ranker     |
| 4. Patches broken procedural steps |   | 4. 1-Hop Entity Subgraph Join  |
+-----------------+------------------+   +----------------+---------------+
                  |                                       |
                  +-------------------+-------------------+
                                      |
                                      v
+-------------------------------------------------------------------------+
|          NEON SERVERLESS POSTGRESQL 16 (or Local pgvector Docker)       |
|   Pooled Endpoint (`-pooler` PgBouncer + SSL) & Direct Migration URI    |
|        (`pgvector` 768-dim HNSW + `tsvector` GIN + `JSONB`)             |
|                                                                         |
|  +------------------+  +-----------------------+  +------------------+  |
|  |    `memories`    |  | `procedural_memories` |  |  `entity_nodes`  |  |
|  | (Semantic &      |  | (Versioned Steps,     |  |        &         |  |
|  |  Episodic Rows)  |  |  Success/Fail Rate)   |  |  `entity_edges`  |  |
|  +------------------+  +-----------------------+  +------------------+  |
+-------------------------------------------------------------------------+
```

---

## 3. Target Directory Structure

Antigravity must generate the complete standalone repository matching this exact file tree:

```text
strata-memory/
├── pyproject.toml                # Package config, dependencies & CLI scripts
├── .env.example                  # Neon Postgres URLs, FastEmbed & Local LLM config
├── docker-compose.yml            # Optional local fallback (pgvector/pgvector:pg16)
├── README.md                     # Setup, Neon DB branching workflow, MCP & API docs
├── sql/
│   └── 001_init_schema.sql       # Complete 4-pillar DDL + HNSW indexes + RRF SQL function
├── src/
│   └── strata/
│       ├── __init__.py
│       ├── config.py             # Pydantic Settings (Neon Pooled + Direct URLs)
│       ├── models.py             # Pydantic v2 schemas for all 4 pillars & tool I/O
│       ├── embedder.py           # Singleton FastEmbed (BAAI/bge-base-en-v1.5, 768-dim)
│       ├── db.py                 # Neon-optimized asyncpg pool + auto-migration runner
│       ├── llm_processor/
│       │   ├── __init__.py
│       │   ├── prompts.py        # System prompts for 4-pillar extraction & procedure evolution
│       │   └── router.py         # Small LLM decision processor + fast_mode bypass
│       ├── pillars/
│       │   ├── __init__.py
│       │   ├── semantic.py       # Bi-temporal fact storage & contradiction superseding
│       │   ├── episodic.py       # Immutable event logging & utility score updates
│       │   ├── procedural.py     # Versioned workflow CRUD, Bayesian ranking & patching
│       │   └── entity_graph.py   # Bi-temporal node/edge upsert & 1-hop subgraph traversal
│       ├── recall.py             # Unified deterministic recall & token-budget XML packer
│       ├── mcp_server.py         # FastMCP server entrypoint (stdio & SSE)
│       └── rest_api.py           # FastAPI HTTP server entrypoint
└── tests/
    └── test_strata.py            # Async integration test suite for all 4 pillars & RRF
```

---

## 4. Configuration & Package Files

### 4.1 `pyproject.toml`
```toml
[project]
name = "strata-memory"
version = "0.1.0"
description = "Strata: Standalone 4-Pillar Cognitive Memory Engine on Neon PostgreSQL"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "asyncpg>=0.29.0",
    "fastembed>=0.3.6",
    "fastmcp>=0.4.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "openai>=1.50.0",
    "pydantic>=2.8.0",
    "pydantic-settings>=2.4.0",
    "python-dotenv>=1.0.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
]

[project.scripts]
strata-mcp = "strata.mcp_server:main"
strata-api = "strata.rest_api:main"
strata-migrate = "strata.db:run_migrations_cli"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 4.2 `.env.example` (Neon PostgreSQL Ready)
```ini
# ============================================================================
# 1. NEON SERVERLESS POSTGRESQL CONFIGURATION
# ============================================================================
# Pooled connection string (with -pooler suffix) for high-concurrency runtime queries
DATABASE_URL="postgresql://neondb_owner:YOUR_PASSWORD@ep-cool-frost-123456-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"

# Direct connection string (without -pooler) used for running DDL migrations
DIRECT_DATABASE_URL="postgresql://neondb_owner:YOUR_PASSWORD@ep-cool-frost-123456.us-east-2.aws.neon.tech/neondb?sslmode=require"

# Set to 0 when using Neon's -pooler (PgBouncer transaction mode) to avoid prepared statement collisions
DB_STATEMENT_CACHE_SIZE=0
DB_POOL_MIN_SIZE=1
DB_POOL_MAX_SIZE=10

# ============================================================================
# 2. LOCAL EMBEDDING ENGINE (FASTEMBED ONNX)
# ============================================================================
EMBEDDING_MODEL_NAME="BAAI/bge-base-en-v1.5"
EMBEDDING_DIMENSIONS=768

# ============================================================================
# 3. MEMORY-SIDE SMALL DECISION LLM (OPTION 1: AUTONOMOUS EXTRACTION)
# ============================================================================
# Compatible with Ollama (http://localhost:11434/v1) or LM Studio (http://localhost:1234/v1)
MEMORY_LLM_ENABLED=true
MEMORY_LLM_BASE_URL="http://localhost:11434/v1"
MEMORY_LLM_API_KEY="ollama"
MEMORY_LLM_MODEL="qwen2.5:3b-instruct"
MEMORY_LLM_TIMEOUT_SECONDS=15.0

# ============================================================================
# 4. SERVER CONFIGURATION
# ============================================================================
STRATA_DEFAULT_NAMESPACE="default"
STRATA_API_HOST="0.0.0.0"
STRATA_API_PORT=8080
```

---

## 5. Complete Database Schema & RRF Function (`sql/001_init_schema.sql`)

This SQL script runs cleanly on **Neon PostgreSQL** (as well as any local `pgvector` Postgres instance). Note that vector serialization in `asyncpg` uses text-casting (`$1::vector(768)`) so it works seamlessly without third-party C extensions.

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================================
-- 1. SEMANTIC & EPISODIC MEMORIES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS memories (
    memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace TEXT NOT NULL DEFAULT 'default',
    type TEXT NOT NULL CHECK (type IN ('semantic', 'episodic')),
    summary TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    tags TEXT[] NOT NULL DEFAULT '{}',
    embedding VECTOR(768) NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 1.0,
    utility_score INT NOT NULL DEFAULT 0,
    access_count INT NOT NULL DEFAULT 0,
    source_id TEXT,
    superseded_by UUID REFERENCES memories(memory_id) ON DELETE SET NULL,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ DEFAULT NULL, -- NULL means currently active/valid
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memories_ns_type_active
    ON memories (namespace, type) WHERE valid_until IS NULL;

CREATE INDEX IF NOT EXISTS idx_memories_embedding_hnsw
    ON memories USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_memories_summary_fts
    ON memories USING gin (to_tsvector('english', summary));

-- ============================================================================
-- 2. PROCEDURAL MEMORY TABLE (SELF-EVOLVING WORKFLOWS & RUNBOOKS)
-- ============================================================================
CREATE TABLE IF NOT EXISTS procedural_memories (
    procedure_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace TEXT NOT NULL DEFAULT 'default',
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    trigger_condition TEXT NOT NULL,
    trigger_embedding VECTOR(768) NOT NULL,
    steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    prerequisites JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INT NOT NULL DEFAULT 1,
    changelog JSONB NOT NULL DEFAULT '[]'::jsonb,
    success_count INT NOT NULL DEFAULT 0,
    fail_count INT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(namespace, name)
);

CREATE INDEX IF NOT EXISTS idx_procedural_trigger_hnsw
    ON procedural_memories USING hnsw (trigger_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ============================================================================
-- 3. ENTITY GRAPH MEMORY TABLES (BI-TEMPORAL NODES & EDGES)
-- ============================================================================
CREATE TABLE IF NOT EXISTS entity_nodes (
    entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace TEXT NOT NULL DEFAULT 'default',
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding VECTOR(768) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(namespace, name, entity_type)
);

CREATE INDEX IF NOT EXISTS idx_entity_nodes_embedding_hnsw
    ON entity_nodes USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE TABLE IF NOT EXISTS entity_edges (
    edge_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace TEXT NOT NULL DEFAULT 'default',
    source_entity_id UUID NOT NULL REFERENCES entity_nodes(entity_id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    target_entity_id UUID NOT NULL REFERENCES entity_nodes(entity_id) ON DELETE CASCADE,
    fact_summary TEXT NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_entity_edges_active
    ON entity_edges (namespace, source_entity_id, target_entity_id)
    WHERE valid_until IS NULL;

-- ============================================================================
-- 4. RECIPROCAL RANK FUSION (RRF) + UTILITY SCORE SQL FUNCTION
-- ============================================================================
CREATE OR REPLACE FUNCTION hybrid_memory_search(
    query_text TEXT,
    query_embedding VECTOR(768),
    target_namespace TEXT,
    target_types TEXT[],
    match_threshold FLOAT DEFAULT 0.45,
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    memory_id UUID,
    type TEXT,
    summary TEXT,
    payload JSONB,
    tags TEXT[],
    utility_score INT,
    confidence FLOAT,
    created_at TIMESTAMPTZ,
    rrf_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    WITH vector_matches AS (
        SELECT
            m.memory_id,
            m.type,
            m.summary,
            m.payload,
            m.tags,
            m.utility_score,
            m.confidence,
            m.created_at,
            ROW_NUMBER() OVER (ORDER BY (m.embedding <=> query_embedding) ASC) AS rank_vec
        FROM memories m
        WHERE m.namespace = target_namespace
          AND m.type = ANY(target_types)
          AND m.valid_until IS NULL
          AND (1.0 - (m.embedding <=> query_embedding)) >= match_threshold
        LIMIT 50
    ),
    text_matches AS (
        SELECT
            m.memory_id,
            m.type,
            m.summary,
            m.payload,
            m.tags,
            m.utility_score,
            m.confidence,
            m.created_at,
            ROW_NUMBER() OVER (
                ORDER BY ts_rank_cd(
                    to_tsvector('english', m.summary),
                    websearch_to_tsquery('english', query_text)
                ) DESC
            ) AS rank_txt
        FROM memories m
        WHERE m.namespace = target_namespace
          AND m.type = ANY(target_types)
          AND m.valid_until IS NULL
          AND query_text <> ''
          AND to_tsvector('english', m.summary) @@ websearch_to_tsquery('english', query_text)
        LIMIT 50
    ),
    fused AS (
        SELECT
            COALESCE(v.memory_id, t.memory_id) AS memory_id,
            COALESCE(v.type, t.type) AS type,
            COALESCE(v.summary, t.summary) AS summary,
            COALESCE(v.payload, t.payload) AS payload,
            COALESCE(v.tags, t.tags) AS tags,
            COALESCE(v.utility_score, t.utility_score) AS utility_score,
            COALESCE(v.confidence, t.confidence) AS confidence,
            COALESCE(v.created_at, t.created_at) AS created_at,
            (
                COALESCE(1.0 / (60.0 + v.rank_vec), 0.0) +
                COALESCE(1.0 / (60.0 + t.rank_txt), 0.0) +
                (LEAST(GREATEST(COALESCE(v.utility_score, t.utility_score), -5), 20) * 0.001)
            )::FLOAT AS score
        FROM vector_matches v
        FULL OUTER JOIN text_matches t ON v.memory_id = t.memory_id
    )
    SELECT
        f.memory_id,
        f.type,
        f.summary,
        f.payload,
        f.tags,
        f.utility_score,
        f.confidence,
        f.created_at,
        f.score AS rrf_score
    FROM fused f
    ORDER BY f.score DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;
```

---

## 6. Core Implementation Specification by Module

### 6.1 `src/strata/config.py` (Neon-Aware Settings)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class StrataSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    direct_database_url: Optional[str] = None
    db_statement_cache_size: int = 0  # Required 0 for Neon -pooler (PgBouncer transaction mode)
    db_pool_min_size: int = 1
    db_pool_max_size: int = 10

    embedding_model_name: str = "BAAI/bge-base-en-v1.5"
    embedding_dimensions: int = 768

    memory_llm_enabled: bool = True
    memory_llm_base_url: str = "http://localhost:11434/v1"
    memory_llm_api_key: str = "ollama"
    memory_llm_model: str = "qwen2.5:3b-instruct"
    memory_llm_timeout_seconds: float = 15.0

    strata_default_namespace: str = "default"
    strata_api_host: str = "0.0.0.0"
    strata_api_port: int = 8080

settings = StrataSettings()
```

### 6.2 `src/strata/embedder.py` (768-Dim Local FastEmbed + pgvector Formatter)
```python
from typing import List
from fastembed import TextEmbedding
from strata.config import settings

class LocalEmbedder:
    _instance: "LocalEmbedder | None" = None

    def __init__(self) -> None:
        self.model = TextEmbedding(model_name=settings.embedding_model_name)

    @classmethod
    def get_instance(cls) -> "LocalEmbedder":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def embed_one(self, text: str) -> List[float]:
        vec = next(self.model.embed([text]))
        return vec.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [v.tolist() for v in self.model.embed(texts)]

    @staticmethod
    def to_pgvector_str(vec: List[float]) -> str:
        """Formats a float list into pgvector literal '[0.1,0.2,...]' for asyncpg."""
        return "[" + ",".join(f"{x:.7f}" for x in vec) + "]"
```

### 6.3 `src/strata/db.py` (Neon Serverless Connection Pool & Migration Runner)
* **Critical Neon Requirement:** Neon's `-pooler` endpoint uses PgBouncer in `transaction` mode, and Neon serverless computes may scale to zero when idle. Therefore, `asyncpg.create_pool()` **must** be initialized with:
  * `statement_cache_size=settings.db_statement_cache_size` (`0` by default)
  * `max_inactive_connection_lifetime=300.0`
  * Custom JSON/JSONB codecs registered on connection init or clean `json.dumps` / `json.loads` serialization.
* Include `run_migrations()` which connects via `settings.direct_database_url or settings.database_url` and executes `sql/001_init_schema.sql`.

### 6.4 `src/strata/models.py` (Pydantic Data Contracts)
Define strict Pydantic v2 models for:
1. **LLM Extraction Plan (`MemoryExtractionPlan`):**
   * `semantic_ops: List[SemanticExtractionOp]` (`action: Literal["ADD", "SUPERSEDE", "IGNORE"]`, `supersede_memory_id: Optional[str]`, `summary: str`, `tags: List[str]`, `confidence: float`)
   * `episodic_ops: List[EpisodicExtractionOp]` (`summary: str`, `situation: str`, `action_taken: str`, `outcome: str`, `success: bool`, `tags: List[str]`)
   * `procedural_ops: List[ProceduralExtractionOp]` (`action: Literal["CREATE", "UPDATE"]`, `name: str`, `description: str`, `trigger_condition: str`, `steps: List[str]`, `prerequisites: dict`, `reason_for_change: str`)
   * `entity_ops: List[EntityExtractionOp]` (`source_name: str`, `source_type: str`, `source_summary: str`, `relation_type: str`, `target_name: str`, `target_type: str`, `target_summary: str`, `fact_summary: str`, `invalidate_conflicting_relations: bool = True`)
2. **Recall Request & Response (`RecallRequest`, `RecallResponse`):**
   * Returns structured lists (`semantic`, `episodic`, `procedural`, `entities`) plus `formatted_context: str` (XML block trimmed to `token_budget`).

### 6.5 `src/strata/pillars/` (The 4 Pillar Storage Modules)
1. **`semantic.py`:**
   * `add_or_supersede_semantic()`: If `supersede_memory_id` is provided (or if an existing active semantic memory in the same `namespace` has cosine similarity `> 0.94`), insert the new fact and update the old row: `SET valid_until = NOW(), superseded_by = $new_id`.
2. **`episodic.py`:**
   * `record_episode()`: Append-only `INSERT` into `memories` with `type = 'episodic'` and structured JSONB `payload` (`situation`, `action_taken`, `outcome`, `success`).
   * `update_utility_scores(memory_ids: List[str], delta: int)`: Updates `utility_score = utility_score + $delta` after an agent run succeeds (`+1`) or fails (`-2`).
3. **`procedural.py`:**
   * `upsert_procedure()`: Inserts a new procedure or updates an existing one by `(namespace, name)`, incrementing `version = version + 1` and appending `{version, timestamp, reason}` to `changelog`.
   * `search_procedures(query_embedding, namespace, top_k)`: Ranks active procedures using the composite Bayesian formula:
     $$\text{Score} = 0.75 \times (1 - \text{CosineDistance}) + 0.25 \times \left(\frac{\text{success\_count} + 1}{\text{success\_count} + \text{fail\_count} + 2}\right)$$
   * `record_procedure_feedback(namespace, name, success, patched_steps, failure_reason)`: Increments `success_count` or `fail_count`, and if `patched_steps` are provided, bumps `version` and records the fix.
4. **`entity_graph.py`:**
   * `upsert_entity_link()`: Upserts `source` and `target` nodes into `entity_nodes` (`ON CONFLICT (namespace, name, entity_type) DO UPDATE`). If `invalidate_conflicting_relations=True`, marks prior active edges with the same `(namespace, source_entity_id, relation_type)` as `valid_until = NOW()`, then inserts the new active edge.
   * `search_entity_subgraph(query_embedding, query_text, namespace, top_k)`: Finds top matching `entity_nodes` via vector similarity or `ILIKE` name match, then performs a 1-hop `JOIN` across `entity_edges` (`WHERE valid_until IS NULL`) to return active entity triplets `(Source) -[Relation]-> (Target)`.

### 6.6 `src/strata/llm_processor/` (Memory-Side Small LLM Router)
* **`prompts.py`:** Contains two battle-tested system prompts:
  1. `EXTRACTION_SYSTEM_PROMPT`: Instructs the small LLM to inspect `EXISTING_SIMILAR_MEMORIES` and `NEW_RAW_INPUT`, split the input into `semantic_ops`, `episodic_ops`, `procedural_ops`, and `entity_ops`, set `action="SUPERSEDE"` when a new fact contradicts an existing memory ID, and output strict JSON.
  2. `PROCEDURE_PATCH_PROMPT`: Given a failed procedure's current `steps[]` and the agent's `failure_reason`, outputs revised `steps[]` that prevent the failure on future runs.
* **`router.py`:**
  * Implements `process_and_ingest(raw_text: str, namespace: str, fast_mode: bool = False, default_type: str = "semantic")`.
  * When `fast_mode=False` and `settings.memory_llm_enabled=True`:
    1. Embeds `raw_text` once with `LocalEmbedder`.
    2. Prefetches top 5 active semantic memories, top 3 procedures, and top 5 entity nodes in parallel.
    3. Calls the local OpenAI-compatible LLM (`response_format={"type": "json_object"}`).
    4. Executes all resulting pillar operations inside a database transaction and returns a detailed summary of created/superseded/updated IDs.
  * **Graceful Fallback:** If the local LLM is offline or times out, or if `fast_mode=True`, automatically falls back to deterministic storage into the `memories` table so the agent never crashes.

### 6.7 `src/strata/recall.py` (Deterministic Multi-Pillar Recall & Token Budgeter)
* Runs `hybrid_memory_search` (for Semantic and Episodic), `search_procedures` (for Procedural), and `search_entity_subgraph` (for Entity) concurrently via `asyncio.gather`.
* Increments `access_count` asynchronously on retrieved rows.
* Formats a clean XML context block respecting `token_budget` (approximated as `len(text) // 4`):
```xml
<strata_memory_context namespace="default">
  <semantic_facts>
    - [mem_id=...] User prefers PostgreSQL with pgvector on Neon serverless.
  </semantic_facts>
  <entity_graph>
    - (Dheeban [person]) -[BUILDS]-> (Velora [project]): Founder and solo developer
  </entity_graph>
  <procedural_skills>
    - [skill=deploy_neon_migration v2 | success_rate=92%] Trigger: When running schema migrations...
      Steps: 1. Use DIRECT_DATABASE_URL... 2. Verify pgvector extension...
  </procedural_skills>
  <episodic_history>
    - [2026-11-14 | outcome=SUCCESS] Fixed PgBouncer prepared statement error by setting statement_cache_size=0.
  </episodic_history>
</strata_memory_context>
```

---

## 7. Unified MCP Server & FastAPI Endpoints

Expose these **6 tools/endpoints** in both `src/strata/mcp_server.py` (`FastMCP("Strata Memory Engine")`) and `src/strata/rest_api.py` (`FastAPI`):

1. **`memory_ingest(raw_text: str, namespace: str = "default", fast_mode: bool = False, source_id: Optional[str] = None)`**
   * Autonomous 4-pillar extraction & storage using the Memory-Side Small LLM (or direct semantic insert if `fast_mode=True`).
2. **`memory_recall(query: str, namespace: str = "default", pillars: List[str] = ["semantic", "episodic", "procedural", "entity"], top_k: int = 5, token_budget: int = 1500)`**
   * Zero-LLM, <15ms hybrid RRF + graph + procedural retrieval.
3. **`memory_store_explicit(pillar: Literal["semantic", "episodic", "procedural", "entity"], payload: dict, namespace: str = "default")`**
   * Direct, zero-LLM structured write to any of the 4 pillars when the calling agent has already structured the data.
4. **`memory_edit(target_id_or_name: str, instruction: str, pillar: Literal["semantic", "procedural", "entity"] = "semantic", namespace: str = "default")`**
   * Uses the Memory-Side Small LLM to apply a natural language modification or supersede operation to an existing memory or procedure.
5. **`memory_feedback(memory_ids_used: List[str] = [], procedure_name: Optional[str] = None, success: bool = True, failure_reason: Optional[str] = None, namespace: str = "default")`**
   * Updates `utility_score` on `memory_ids_used` (`+1` on success, `-2` on failure). If `procedure_name` failed and `failure_reason` is provided, uses the Small LLM to auto-patch the procedure's steps and increment its `version`.
6. **`memory_delete(target_id: str, pillar: Literal["semantic", "episodic", "procedural", "entity"] = "semantic", hard_delete: bool = False, namespace: str = "default")`**
   * Soft-invalidates (`valid_until = NOW()` or `is_active = FALSE`) by default, or permanently deletes if `hard_delete=True`.

---

## 8. Execution Prompt for Antigravity

Copy and paste this exact prompt to Antigravity:

> **"Read `strata_4_pillar_memory_engine_specification.md` and build the complete `strata-memory` standalone project from start to finish. Create all files in the target directory structure (`pyproject.toml`, `.env.example`, `docker-compose.yml`, `sql/001_init_schema.sql`, all modules under `src/strata/`, and `tests/test_strata.py`). Ensure `db.py` supports Neon Serverless PostgreSQL (`sslmode=require` and `statement_cache_size=0` for PgBouncer compatibility) and passes `pgvector` embeddings safely as formatted vector strings (`$1::vector(768)`). Implement complete, production-ready async code with zero placeholders or TODOs."**