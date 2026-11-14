# Strata: Standalone Autonomous 4-Pillar Memory Engine (Neon Postgres Edition)

Just as geological strata preserve layered history over time, **Strata** is a standalone, plug-and-play **4-Pillar Cognitive Memory Engine** powered by **Neon Serverless PostgreSQL (`pgvector` + `tsvector` + `JSONB`)**.

Universal connectivity: Any agent, IDE, or framework (LangGraph, CrewAI, AutoGen, Claude Desktop, Cursor, etc.) connects to Strata via **FastMCP (stdio/SSE)**, **FastAPI REST HTTP**, or direct **Python SDK**.

---

## 🏛️ The 4 Cognitive Memory Pillars

1. **Semantic Layer:** Atomic facts, user preferences, configurations, and domain truths with bi-temporal validity (`valid_from`, `valid_until`, `superseded_by`). Contradictions are superseded automatically.
2. **Episodic Layer:** Immutable timestamped execution traces, events, situations, actions, outcomes, and utility scores (`+1` on success, `-2` on failure).
3. **Procedural Layer:** Mutable, versioned step-by-step workflows, skills, and runbooks ranked by a composite Bayesian formula ($\text{Score} = 0.75 \times \text{Sim} + 0.25 \times \frac{\text{success} + 1}{\text{total} + 2}$) that self-evolve when failures occur.
4. **Entity Layer:** Bi-temporal property graph of people, projects, services, repositories, and servers with 1-hop subgraph traversal.

---

## ⚡ Dual-Path Architecture with Laya Decision Pre-Routing

* **Deterministic Read Path (<15ms, Zero-LLM):**
  Embeds queries asynchronously via **Ollama** (`nomic-embed-text`, 768 dimensions) and executes a single-round-trip SQL query on Neon Postgres combining **Reciprocal Rank Fusion (RRF)** (`pgvector` HNSW cosine similarity + `tsvector` full-text search) + Bayesian Procedural ranking + 1-hop Entity Graph traversal, packed neatly into the caller's token budget with configurable score thresholds (`min_score`, `match_threshold`, `similarity_threshold`).
* **Intelligent Write Path (Laya Decision Engine + Small LLM):**
  - **Laya Pre-Routing Fast Path (<5ms, Zero-LLM):** Fast decision classifier checks input complexity, signals, and contradiction against pre-fetched memories. For simple atomic facts, execution events, entity triples, and updates, Laya performs direct template extraction and superseding (<15ms, 0 tokens).
  - **Generative Multi-Pillar Router (Small LLM `qwen3:8b`):** Complex multi-pillar narratives, mixed contradictory updates, and procedure error repairs are seamlessly escalated to the Small LLM for full JSON plan generation.
  - **Graceful Deterministic Fallback:** Operates reliably even if Ollama/LLM endpoints are offline.

---

## 🚀 Quickstart with Neon Serverless PostgreSQL

### 1. Configure Neon Connection Strings

Neon provides two connection strings:
1. **Pooled Connection (`-pooler` suffix):** Uses PgBouncer in transaction mode for high-concurrency runtime queries. Requires `statement_cache_size=0`.
2. **Direct Connection (without `-pooler`):** Used for DDL schema migrations.

Copy `.env.example` to `.env` and fill in your Neon credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```ini
DATABASE_URL="postgresql://neondb_owner:YOUR_PASSWORD@ep-xyz-123456-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
DIRECT_DATABASE_URL="postgresql://neondb_owner:YOUR_PASSWORD@ep-xyz-123456.us-east-2.aws.neon.tech/neondb?sslmode=require"
DB_STATEMENT_CACHE_SIZE=0

# Embedding model via Ollama
EMBEDDING_PROVIDER="ollama"
EMBEDDING_BASE_URL="http://localhost:11434/v1"
EMBEDDING_MODEL_NAME="nomic-embed-text"
EMBEDDING_DIMENSIONS=768

# Memory-side Small LLM via Ollama
MEMORY_LLM_ENABLED=true
MEMORY_LLM_BASE_URL="http://localhost:11434/v1"
MEMORY_LLM_MODEL="qwen3:8b"

# Laya Decision Model Pre-routing
LAYA_ENABLED=true
LAYA_COMPLEXITY_THRESHOLD=2
LAYA_FALLBACK_TO_LLM=true

# Dynamic Tuning Defaults
RECALL_MATCH_THRESHOLD=0.35
RECALL_MIN_SCORE=0.0
ENTITY_SIMILARITY_THRESHOLD=0.40
CONTRADICTION_THRESHOLD=0.94
```

### 2. Install Dependencies

Using `uv` (recommended):
```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

Or using standard `pip`:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. Run Neon Schema Migrations

Apply the 4-pillar schema and RRF function to your Neon database:
```bash
strata-migrate
```

---

## 🛠️ Running Strata

### Option A: FastMCP Server (Claude Desktop / Cursor IDE)

Run directly via stdio:
```bash
strata-mcp --transport stdio
```

#### 1. Claude Desktop Configuration (`claude_desktop_config.json`)
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "strata-memory": {
      "command": "/Users/dheeban/Documents/my_projects/ai-engineering-lab/strata-memory/.venv/bin/strata-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "DATABASE_URL": "postgresql://neondb_owner:YOUR_PASSWORD@ep-xyz-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require",
        "DIRECT_DATABASE_URL": "postgresql://neondb_owner:YOUR_PASSWORD@ep-xyz.ap-southeast-1.aws.neon.tech/neondb?sslmode=require",
        "DB_STATEMENT_CACHE_SIZE": "0",
        "NEON_KEEP_ALIVE": "false",
        "NEON_API_KEY": "",
        "NEON_PROJECT_ID": "your-project-id",
        "NEON_ENDPOINT_ID": "ep-xyz",
        "EMBEDDING_PROVIDER": "ollama",
        "EMBEDDING_BASE_URL": "http://localhost:11434/v1",
        "EMBEDDING_API_KEY": "ollama",
        "EMBEDDING_MODEL_NAME": "nomic-embed-text",
        "EMBEDDING_DIMENSIONS": "768",
        "MEMORY_LLM_ENABLED": "true",
        "MEMORY_LLM_BASE_URL": "http://localhost:11434/v1",
        "MEMORY_LLM_API_KEY": "ollama",
        "MEMORY_LLM_MODEL": "qwen3:8b",
        "MEMORY_LLM_TIMEOUT_SECONDS": "120.0",
        "LAYA_ENABLED": "true",
        "LAYA_COMPLEXITY_THRESHOLD": "2",
        "LAYA_FALLBACK_TO_LLM": "true",
        "RECALL_MATCH_THRESHOLD": "0.35",
        "RECALL_MIN_SCORE": "0.0",
        "ENTITY_SIMILARITY_THRESHOLD": "0.40",
        "CONTRADICTION_THRESHOLD": "0.94",
        "STRATA_DEFAULT_NAMESPACE": "default"
      }
    }
  }
}
```

#### 2. Cursor IDE Configuration (`.cursor/mcp.json` or `~/.cursor/mcp.json`)
Place this in `.cursor/mcp.json` in your project root or in Cursor's global MCP settings:
```json
{
  "mcpServers": {
    "strata-memory": {
      "command": "/Users/dheeban/Documents/my_projects/ai-engineering-lab/strata-memory/.venv/bin/strata-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "DATABASE_URL": "postgresql://neondb_owner:YOUR_PASSWORD@ep-xyz-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require",
        "DIRECT_DATABASE_URL": "postgresql://neondb_owner:YOUR_PASSWORD@ep-xyz.ap-southeast-1.aws.neon.tech/neondb?sslmode=require",
        "DB_STATEMENT_CACHE_SIZE": "0",
        "NEON_KEEP_ALIVE": "false",
        "NEON_API_KEY": "",
        "NEON_PROJECT_ID": "your-project-id",
        "NEON_ENDPOINT_ID": "ep-xyz",
        "EMBEDDING_PROVIDER": "ollama",
        "EMBEDDING_BASE_URL": "http://localhost:11434/v1",
        "EMBEDDING_API_KEY": "ollama",
        "EMBEDDING_MODEL_NAME": "nomic-embed-text",
        "EMBEDDING_DIMENSIONS": "768",
        "MEMORY_LLM_ENABLED": "true",
        "MEMORY_LLM_BASE_URL": "http://localhost:11434/v1",
        "MEMORY_LLM_API_KEY": "ollama",
        "MEMORY_LLM_MODEL": "qwen3:8b",
        "MEMORY_LLM_TIMEOUT_SECONDS": "120.0",
        "LAYA_ENABLED": "true",
        "LAYA_COMPLEXITY_THRESHOLD": "2",
        "LAYA_FALLBACK_TO_LLM": "true",
        "RECALL_MATCH_THRESHOLD": "0.35",
        "RECALL_MIN_SCORE": "0.0",
        "ENTITY_SIMILARITY_THRESHOLD": "0.40",
        "CONTRADICTION_THRESHOLD": "0.94",
        "STRATA_DEFAULT_NAMESPACE": "default"
      }
    }
  }
}
```
*(A ready-to-copy template with environment variables is also available at [`mcp.example.json`](mcp.example.json))*

Run as SSE server for remote agents:
```bash
strata-mcp --transport sse --host 0.0.0.0 --port 8000
```

### Option B: FastAPI REST HTTP Server

Start the REST API:
```bash
strata-api
```
Endpoints:
- `POST /v1/memory/ingest`: Autonomous 4-pillar extraction & storage (with optional TTL).
- `POST /v1/memory/recall`: Deterministic hybrid RRF retrieval (<15ms).
- `POST /v1/memory/store`: Direct structured write to any pillar (with optional TTL).
- `POST /v1/memory/edit`: Natural language modification / supersede.
- `POST /v1/memory/feedback`: Utility score adjustment & auto-patching of failed runbooks.
- `POST /v1/memory/delete`: Soft or hard deletion.
- `POST /v1/memory/prune`: Cognitive distillation of expiring episodes into runbooks & physical purge.
- `POST /v1/memory/purge-namespace`: Transactional wipe of an entire namespace (GDPR / reset).
- `GET /health`: Health check.

Interactive Swagger documentation is available at `http://localhost:8080/docs`.

---

## 📖 Documentation & Unified Guides

- 👉 **[docs/architecture_and_internals.md](docs/architecture_and_internals.md)**: Complete engineering manual — 4-pillar internals, Neon Postgres storage layout, bi-temporal active state management, $O(\log N)$ HNSW scalability, Laya Decision Pre-Routing, and sequence diagrams.
- 👉 **[docs/agent_integration_and_access.md](docs/agent_integration_and_access.md)**: Universal connectivity handbook — All 7 access methods (Python SDK, FastMCP stdio/SSE, REST API, Swagger), Claude Desktop & Cursor setup, LangGraph/CrewAI agent integrations, and the System Prompt handbook.
- 👉 **[docs/operations_reference.md](docs/operations_reference.md)**: Complete API & Tool reference — Detailed parameters, dynamic thresholds (`min_score`, `match_threshold`, `contradiction_threshold`), 4-pillar payload schemas, and Neon auto-suspend lifecycle.

---

## 🔬 End-to-End Evaluation Pipeline (`tests/eval_pipeline.py`)

Strata includes a production-grade, end-to-end evaluation pipeline that rigorously exercises all 4 cognitive memory pillars, confirms **Laya Decision Engine (<5ms Fast Path)** vs **Generative Small Decision LLM (`qwen3:8b`)** pre-routing, and guarantees zero database pollution using dedicated namespace isolation.

### Strict Isolation & Cleanup Guarantees
- **Dedicated Namespace:** All evaluation operations execute strictly within `NAMESPACE = "eval_dedicated_suite"`.
- **Pre-flight DB Hygiene Check:** Before any test case runs, the suite invokes `svc_memory_purge_namespace("eval_dedicated_suite", confirm=True)` and verifies with direct SQL count queries that `memories`, `procedural_memories`, `entity_edges`, and `entity_nodes` are strictly at **0 rows**.
- **Post-flight Guaranteed Clean Slate:** The final cleanup runs inside an unconditional `finally:` block. Even if an assertion or unhandled exception occurs, all evaluation records are wiped clean, confirming 0 lingering artifacts in Neon PostgreSQL.

### Comprehensive Evaluation Suite Matrix (12 Cases)

| Pillar | Test Case | Handler Verified | Core Invariants Verified |
| :--- | :--- | :--- | :--- |
| **Semantic** | **Case 1A:** Simple Fact / Preference Ingest | **Laya Decision Model** (`mode: "laya_decision"`) | Single fact parsed without waking LLM; `type: "semantic"`, `valid_until: NULL`, routing latency <15ms. |
| **Semantic** | **Case 1B:** Contradiction & Superseding | **Laya Decision Model** (`mode: "laya_decision"`) | Explicit update detected; previous fact marked with `valid_until = NOW()` and `superseded_by = new_id`. Query returns only new fact. |
| **Semantic** | **Case 1C:** Ephemeral TTL Expiration | **Strata Storage Engine** (SQL filter) | Fact stored with `ttl_seconds=1` is recallable immediately, but automatically excluded post-1.5s via `(valid_until > NOW())`. |
| **Episodic** | **Case 2A:** Direct Incident Log Ingest | **Laya Decision Model** (`mode: "laya_decision"`) | Failure/incident log classified without LLM; `outcome: "failed"`, `success: false` recorded in JSONB payload. |
| **Episodic** | **Case 2B:** Utility Score Feedback Loop | **Dynamic Reinforcement Engine** | `svc_memory_feedback` adjusts utility scores: `-2` on execution failure, `+1` on success in Neon Postgres. |
| **Episodic** | **Case 2C:** Cognitive Distillation & Prune | **Generative Small LLM & Safe Pruner** | `svc_memory_prune` gathers expiring episodes, synthesizes durable runbooks/facts with Small LLM, then purges raw rows. |
| **Procedural** | **Case 3A:** Runbook Registration & Recall | **Strata Procedural Engine** | Procedural runbook registered (`version=1`, prerequisites, steps); retrieved via Bayesian trigger matching. |
| **Procedural** | **Case 3B:** Self-Healing on Execution Failure | **Generative Small LLM** (`qwen3:8b`) | Failure error trace analyzed by LLM; steps auto-patched, version incremented `v1` $\rightarrow$ `v2`, changelog logged with timestamp. |
| **Entity Graph** | **Case 4A:** Entity Relation Direct Ingest | **Laya Decision Model** (`mode: "laya_decision"`) | Direct relation `(Strata) -[USES]-> (Neon)` extracted without LLM; nodes and edge stored atomically. |
| **Entity Graph** | **Case 4B:** 1-Hop Traversal & Soft Delete | **Strata Graph Engine & Soft Deleter** | 1-hop traversal retrieves connected graph in recall; soft-deleting node marks `is_active = FALSE` and attached edges `valid_until = NOW()`. |
| **Multi-Pillar** | **Case 5:** Compound Multi-Pillar Narrative | **Generative Small LLM** (`qwen3:8b`) | Laya detects complexity conjunction ("However") and multiple active pillars; delegates to Small LLM, which decomposes across all 4 pillars simultaneously. |
| **Recall** | **Case 6:** Zero-LLM Fast Hybrid Recall | **Zero-LLM Fast Path** (<15ms) | RRF vector + keyword + 1-hop graph assembled into formatted `<strata_memory_context>` prompt block under token budget. |

### Database Indexing & Query Optimizations

To ensure sub-millisecond execution even with millions of records, the database schema includes targeted composite B-Tree indexes that eliminate sequential scans (`Seq Scan` $\rightarrow$ `Index Scan`):

* `idx_memories_ns_type_valid_until` on `(namespace, type, valid_until)`: Accelerates active recall queries filtering `(valid_until IS NULL OR valid_until > NOW())`.
* `idx_memories_ns_type_created_at` on `(namespace, type, created_at ASC)`: Accelerates chronological episode compaction & distillation.
* `idx_memories_superseded_by` on `(superseded_by)`: Eliminates foreign key table locks and accelerates bi-temporal lineage audit.
* `idx_entity_edges_tgt` on `(namespace, target_entity_id, valid_until)`: Converts 1-hop incoming graph traversal into instant index scans.
* `idx_entity_edges_src_rel` on `(namespace, source_entity_id, relation_type, valid_until)`: Accelerates outgoing graph traversal and relation conflict resolution.
* `idx_entity_nodes_ns_active` and `idx_procedural_ns_active`: Filtered indexes on active nodes and procedures.

### Running the Evaluation Suite

```bash
# Activate your environment
source .venv/bin/activate

# Option 1: Direct Python Runner
python tests/eval_pipeline.py

# Option 2: Via Pytest (with real-time output)
pytest tests/eval_pipeline.py -v -s
```

---

## 🧪 Testing

Strata provides multiple flexible testing layers that can be run either together in one single command or independently:

### Option A: Run Everything in One Unified Command (Recommended)
Executes all 18 pytest unit/integration tests, followed by the 12-case comprehensive evaluation pipeline, followed by the use-case demo:
```bash
./run_all_tests.sh
```

### Option B: Run by Category

1. **Unit & Integration Tests (18 cases across 4 suites):**
   ```bash
   pytest tests/test_*.py -v
   ```
   - `test_laya_and_dynamics.py`: Laya decision engine pre-routing & classification (<5ms).
   - `test_lifecycle_and_pruning.py`: TTL expiration, toxic retirement, entity soft-delete symmetry, namespace purge.
   - `test_neon_control.py`: Neon connection strings, endpoint parsing, and compute auto-suspension.
   - `test_strata.py`: Embedding dimensions, Pydantic models, XML prompt budget assembly, live CRUD flow.

2. **Comprehensive End-to-End Evaluation Pipeline (12 cases):**
   ```bash
   python tests/eval_pipeline.py
   # or via pytest:
   pytest tests/eval_pipeline.py -v -s
   ```

3. **Interactive Use Case Demo:**
   ```bash
   python examples/demo.py
   ```

---

## 🌿 Neon Database Branching Workflow

Strata pairs seamlessly with Neon's instant copy-on-write database branching:
1. Create a development branch in Neon:
   ```bash
   neon branch create --name dev-experiment
   ```
2. Update `DATABASE_URL` in `.env` to point to the new branch endpoint.
3. Test autonomous ingest, superseding, and procedure self-healing in complete isolation.
