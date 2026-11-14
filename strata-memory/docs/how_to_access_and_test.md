# How to Access and Test the Strata Memory Engine

Strata is designed for **universal compatibility** across autonomous agents, IDEs, web harnesses, and scripts. This guide details **all the different ways to access, interact with, and test Strata**.

---

## 🗺️ Overview: The 7 Ways to Access Strata

| # | Access Method | Protocol / Transport | Primary Use Case | Latency |
|---|---------------|----------------------|------------------|---------|
| **1** | **Python SDK (In-Process)** | Native Python Async | Custom Agent Loops, LangGraph, CrewAI | <15ms |
| **2** | **FastAPI Interactive UI** | HTTP / Browser Swagger | Visual Manual Testing & API Exploration | Low |
| **3** | **REST HTTP API (cURL / HTTP)** | HTTP POST / JSON | Microservices, non-Python runtimes (Node, Go, Rust) | Low |
| **4** | **FastMCP (stdio)** | JSON-RPC over `stdio` | Claude Desktop, Cursor, Zed, Local Agent IDEs | Zero-Network |
| **5** | **FastMCP (SSE)** | Server-Sent Events (HTTP) | Remote Agent Frameworks, Distributed Teams | Network HTTP |
| **6** | **Interactive Demo Script** | Python CLI | Immediate End-to-End Validation | <15ms |
| **7** | **Neon SQL Console / `psql`** | Direct PostgreSQL Wire | Raw Data Inspection, Index Auditing & Debugging | Direct DB |

---

## 1. Python SDK (Direct In-Process Call)

If your external agent is built in Python (e.g. LangGraph, CrewAI, AutoGen, or a custom harness), you can import Strata directly into your process without running an HTTP or MCP daemon.

```python
import asyncio
from strata.service import (
    svc_memory_ingest,
    svc_memory_recall,
    svc_memory_store_explicit,
    svc_memory_feedback,
    svc_memory_delete,
)
from strata.db import close_db_pool

async def main():
    # 1. Store a semantic fact directly
    await svc_memory_store_explicit(
        pillar="semantic",
        payload={"summary": "User prefers dark mode and Python 3.11+."},
        namespace="my_agent",
    )

    # 2. Recall relevant context (<15ms, zero-LLM)
    context = await svc_memory_recall(
        query="What are the user preferences?",
        namespace="my_agent",
        top_k=3,
        token_budget=500,
    )
    print("Recalled XML Block for Agent Prompt:")
    print(context.formatted_context)

    # 3. Clean up DB pool on exit
    await close_db_pool()

asyncio.run(main())
```

---

## 2. Interactive Swagger UI (FastAPI)

Strata provides an interactive web UI powered by Swagger/OpenAPI.

1. **Start the API server:**
   ```bash
   .venv/bin/strata-api
   ```
2. **Open your browser:**
   Navigate to:
   ```
   http://localhost:8080/docs
   ```
3. **Interactive Features:**
   - Click any endpoint (e.g., `POST /v1/memory/recall`), click **"Try it out"**, fill in the JSON parameters, and click **"Execute"**.
   - Inspect status codes, latency, response bodies, and schema documentation.
   - Alternate ReDoc view available at `http://localhost:8080/redoc`.

---

## 3. REST HTTP API via `curl` or HTTP Clients

You can access Strata from any language (JavaScript, TypeScript, Go, Rust, Ruby) via standard JSON POST requests.

### 3.1 Store a Structured Memory
```bash
curl -X POST "http://localhost:8080/v1/memory/store" \
     -H "Content-Type: application/json" \
     -d '{
       "pillar": "semantic",
       "namespace": "production",
       "payload": {
         "summary": "Agent is deployed on Neon PostgreSQL with pgvector.",
         "tags": ["infra", "neon"]
       }
     }'
```

### 3.2 Ingest Unstructured Raw Text (Autonomous Routing)
```bash
curl -X POST "http://localhost:8080/v1/memory/ingest" \
     -H "Content-Type: application/json" \
     -d '{
       "raw_text": "Dheeban founded the Velora project using Neon for persistent memory.",
       "namespace": "production",
       "fast_mode": false
     }'
```

### 3.3 Hybrid Recall (<15ms, Zero-LLM)
```bash
curl -X POST "http://localhost:8080/v1/memory/recall" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What project did Dheeban build and what database does it use?",
       "namespace": "production",
       "top_k": 5,
       "token_budget": 1500
     }'
```

### 3.4 Provide Execution Feedback
```bash
curl -X POST "http://localhost:8080/v1/memory/feedback" \
     -H "Content-Type: application/json" \
     -d '{
       "memory_ids_used": ["<UUID>"],
       "procedure_name": "neon_migration_runbook",
       "success": true,
       "namespace": "production"
     }'
```

---

## 4. FastMCP via `stdio` (Claude Desktop, Cursor, IDEs)

Strata includes a full Model Context Protocol (MCP) server exposing all 6 tools.

### 4.1 Test FastMCP in Terminal
```bash
.venv/bin/strata-mcp --transport stdio
```

### 4.2 Configure Claude Desktop
Add Strata to your `claude_desktop_config.json`:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "strata-memory": {
      "command": "/Users/dheeban/Documents/my_projects/ai-engineering-lab/strata-memory/.venv/bin/strata-mcp",
      "args": ["--transport", "stdio"]
    }
  }
}
```

### 4.3 Configure Cursor IDE
In Cursor **Settings > Features > MCP**:
- Click **"Add New MCP Server"**
- Name: `strata-memory`
- Type: `command`
- Command: `/Users/dheeban/Documents/my_projects/ai-engineering-lab/strata-memory/.venv/bin/strata-mcp --transport stdio`

---

## 5. FastMCP via SSE (Server-Sent Events)

When connecting multiple remote agents or running Strata on a dedicated VM / container:

1. **Start the SSE Server:**
   ```bash
   .venv/bin/strata-mcp --transport sse --host 0.0.0.0 --port 8000
   ```
2. **Connect Remote Clients to SSE Endpoint:**
   ```
   http://localhost:8000/sse
   ```

---

## 6. Interactive Demo Script

An end-to-end Python demo script is located at `examples/demo.py`. It exercises all 4 pillars against your live Neon PostgreSQL database:

```bash
.venv/bin/python examples/demo.py
```

**What it verifies:**
1. Storing facts, procedures, and entities.
2. Generating 768-dim FastEmbed embeddings locally.
3. Querying Neon with `hybrid_memory_search()` (RRF + HNSW + BM25).
4. Generating token-bounded XML context blocks.
5. Updating utility scores with execution feedback.

---

## 7. Direct Neon SQL Console / Inspection

You can inspect the underlying tables, vector embeddings, and RRF calculations directly in your Neon console or via `psql`.

### Connect via `psql`:
```bash
psql "postgresql://neondb_owner:npg_hG04ftzKUaSQ@ep-divine-hill-a1p3fmik.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
```

### Useful SQL Queries:
```sql
-- View all active semantic memories
SELECT memory_id, summary, utility_score, created_at 
FROM memories 
WHERE type = 'semantic' AND valid_until IS NULL;

-- View versioned procedural skills and success rates
SELECT name, version, success_count, fail_count, steps 
FROM procedural_memories;

-- View the active entity graph triples
SELECT 
    src.name AS source, 
    e.relation_type AS relation, 
    tgt.name AS target, 
    e.fact_summary
FROM entity_edges e
JOIN entity_nodes src ON e.source_entity_id = src.entity_id
JOIN entity_nodes tgt ON e.target_entity_id = tgt.entity_id
WHERE e.valid_until IS NULL;
```

---

## 8. Automated Pytest Test Suite

Run the full suite of unit tests and live integration tests:

```bash
.venv/bin/pytest -v
```
