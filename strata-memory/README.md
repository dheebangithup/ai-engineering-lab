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

## ⚡ Dual-Path Architecture

* **Deterministic Read Path (<15ms, Zero-LLM):**
  Embeds queries via **Ollama** (`nomic-embed-text`, 768 dimensions) and executes a single-round-trip SQL query on Neon Postgres combining **Reciprocal Rank Fusion (RRF)** (`pgvector` HNSW cosine similarity + `tsvector` full-text search) + Bayesian Procedural ranking + 1-hop Entity Graph traversal, packed neatly into the caller's token budget.
* **Autonomous Write Path (Memory-Side Intelligence):**
  Uses an internal Small Decision LLM (Ollama, LM Studio, or any OpenAI-compatible endpoint) to extract, categorize, deduplicate, resolve contradictions, and route unstructured text across all 4 pillars. Features graceful deterministic fallback if the LLM is offline.

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

### Option A: FastMCP Server (Claude Desktop / Cursor)

Run directly via stdio:
```bash
strata-mcp --transport stdio
```

Or add to your Claude Desktop config (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "strata-memory": {
      "command": "uv",
      "args": ["--directory", "/path/to/strata-memory", "run", "strata-mcp"]
    }
  }
}
```

Run as SSE server:
```bash
strata-mcp --transport sse --host 0.0.0.0 --port 8000
```

### Option B: FastAPI REST HTTP Server

Start the REST API:
```bash
strata-api
```
Endpoints:
- `POST /v1/memory/ingest`: Autonomous 4-pillar extraction & storage.
- `POST /v1/memory/recall`: Deterministic hybrid RRF retrieval (<15ms).
- `POST /v1/memory/store`: Direct structured write to any pillar.
- `POST /v1/memory/edit`: Natural language modification / supersede.
- `POST /v1/memory/feedback`: Utility score adjustment & auto-patching of failed runbooks.
- `POST /v1/memory/delete`: Soft or hard deletion.
- `GET /health`: Health check.

Interactive Swagger documentation is available at `http://localhost:8080/docs`.

---

## 📖 Documentation & Guides

- 👉 **[docs/agent_integration_and_mcp_guide.md](docs/agent_integration_and_mcp_guide.md)**: How agents discover MCP tool schemas, system prompt guidelines, and LangGraph/Claude integration.
- 👉 **[docs/long_term_scalability_and_edge_cases.md](docs/long_term_scalability_and_edge_cases.md)**: Handling 1 lakh+ records over months/years, constant $O(1)$ Small LLM context, and $O(\log N)$ HNSW retrieval.
- 👉 **[docs/data_storage_active_state_and_recall_guide.md](docs/data_storage_active_state_and_recall_guide.md)**: Deep dive into active vs. superseded states, database storage by pillar, and the recall pipeline.
- 👉 **[docs/architecture_and_component_flow.md](docs/architecture_and_component_flow.md)**: Complete system architecture, subsystem components, sequence diagrams, and Neon data layout.
- 👉 **[docs/how_to_access_and_test.md](docs/how_to_access_and_test.md)**: All 7 ways to access and test Strata (Python SDK, FastAPI Swagger, cURL, FastMCP stdio/SSE, CLI demo, and direct SQL).
- 👉 **[docs/operations_reference.md](docs/operations_reference.md)**: Complete reference of all 6 operations, option filters, scoring formulas, and 4-pillar payload schemas.







---

## 🧪 Testing

Run unit and integration tests:
```bash
pytest -v
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
