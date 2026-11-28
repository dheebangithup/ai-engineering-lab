# Strata Agent Integration, MCP Protocol & Access Guide

This guide is the complete handbook for **connecting external agents, IDEs, web harnesses, and scripts to the Strata Cognitive Memory Engine**. It covers all access protocols, FastMCP setup, REST API usage, agent system prompt engineering, and framework integrations (LangGraph, CrewAI, AutoGen, Claude Desktop, Cursor).

---

## 🗺️ Universal Connectivity Overview: The 7 Access Methods

Strata provides universal connectivity across distributed architectures, local IDEs, and in-process agent loops:

| # | Access Method | Protocol / Transport | Primary Use Case | Latency |
|---|---------------|----------------------|------------------|---------|
| **1** | **Python SDK (In-Process)** | Native Python Async | Custom Agent Loops, LangGraph, CrewAI | <15ms |
| **2** | **FastMCP (stdio)** | JSON-RPC over `stdio` | Claude Desktop, Cursor, Zed, Local Agent IDEs | Zero-Network |
| **3** | **FastMCP (SSE)** | Server-Sent Events (HTTP) | Remote Agent Frameworks, Distributed Teams | Network HTTP |
| **4** | **REST HTTP API (cURL / HTTP)** | HTTP POST / JSON | Microservices, non-Python runtimes (Node, Go, Rust) | Low |
| **5** | **FastAPI Interactive UI** | HTTP / Browser Swagger | Visual Manual Testing & API Exploration at `/docs` | Low |
| **6** | **Interactive CLI Demo** | Python CLI | Immediate End-to-End Local Validation | <15ms |
| **7** | **Neon SQL Console / `psql`** | Direct PostgreSQL Wire | Raw Data Inspection, Index Auditing & Debugging | Direct DB |

---

## 1. Python SDK (Direct In-Process Call)

If your external agent is built in Python (e.g. your personal Jarvis agent, LangGraph, or CrewAI), you can import Strata directly into your process without running an HTTP or MCP daemon.

```python
import asyncio
from strata.service import (
    svc_memory_ingest,
    svc_memory_recall,
    svc_memory_store_explicit,
    svc_memory_feedback,
    svc_memory_delete,
    svc_working_memory_add_tool_output,
    svc_working_memory_unprotect,
    svc_working_memory_get,
)
from strata.db import close_db_pool

async def main():
    namespace = "jarvis_personal"

    # 1. Store a structured memory directly (<10ms, Zero-LLM)
    await svc_memory_store_explicit(
        pillar="semantic",
        payload={"summary": "User prefers dark mode and Python 3.12+."},
        namespace=namespace,
    )

    # 2. Autonomous Ingestion with Laya Decision Model (<15ms for simple, or LLM for complex)
    await svc_memory_ingest(
        raw_text="Dheeban is developing the Strata autonomous cognitive memory engine on Neon.",
        namespace=namespace,
        fast_mode=False,
    )

    # 3. Deterministic Recall (<15ms, Zero-LLM)
    context = await svc_memory_recall(
        query="What are the user preferences and current projects?",
        namespace=namespace,
        top_k=3,
        token_budget=800,
        min_score=0.0,
    )
    print("Recalled XML Block for Agent System Prompt:")
    print(context.formatted_context)

    # 4. Report Task Execution Feedback
    await svc_memory_feedback(
        procedure_name="deploy_service",
        success=True,
        namespace=namespace,
    )

    # 5. Clean up connection pool on shutdown
    await close_db_pool()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 2. FastMCP Server (Claude Desktop, Cursor & Agent IDEs)

Strata includes a full Model Context Protocol (MCP) server exposing all 6 tools to modern AI developer environments.

### 2.1 Running the Server
Run directly via stdio (all logs redirected to `stderr` to keep `stdout` pure for JSON-RPC):
```bash
strata-mcp --transport stdio
```

Or run as an HTTP Server-Sent Events (SSE) server for remote agents:
```bash
strata-mcp --transport sse --host 0.0.0.0 --port 8000
```

### 2.2 Claude Desktop Configuration
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

*Alternative using `uv`:*
```json
{
  "mcpServers": {
    "strata-memory": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/dheeban/Documents/my_projects/ai-engineering-lab/strata-memory",
        "run",
        "strata-mcp",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

### 2.3 Cursor IDE Configuration (`.cursor/mcp.json`)

Cursor reads MCP configurations automatically from project root or global settings:
- **Project-Level (Recommended):** Create `.cursor/mcp.json` in your repository root (a pre-configured copy is included in this repository at [`.cursor/mcp.json`](../.cursor/mcp.json)):
- **Global Settings:** `~/.cursor/mcp.json`

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

*Or via Cursor UI:*
1. Open Cursor **Settings > Features > MCP**.
2. Click **"Add New MCP Server"**.
3. Name: `strata-memory`
4. Type: `command`
5. Command: `/Users/dheeban/Documents/my_projects/ai-engineering-lab/strata-memory/.venv/bin/strata-mcp --transport stdio`

### 2.4 Passing Environment Variables in `mcp.json` (Recommended for Claude Desktop & Cursor)
Claude Desktop and Cursor launch MCP server sub-processes without inheriting your terminal shell's working directory `.env` file by default. Pass the environment variables directly in your MCP JSON configuration (also provided in [`mcp.example.json`](../mcp.example.json) and [`.cursor/mcp.json`](../.cursor/mcp.json)):

```json
{
  "mcpServers": {
    "strata-memory": {
      "command": "/Users/dheeban/Documents/my_projects/ai-engineering-lab/strata-memory/.venv/bin/strata-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "DATABASE_URL": "postgresql://neondb_owner:YOUR_KEY@ep-xyz-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require",
        "DIRECT_DATABASE_URL": "postgresql://neondb_owner:YOUR_KEY@ep-xyz.ap-southeast-1.aws.neon.tech/neondb?sslmode=require",
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
        "MEMORY_LLM_TIMEOUT_SECONDS": "240.0",
        "LAYA_ENABLED": "true",
        "LAYA_MODE": "hybrid",
        "LAYA_OLLAMA_MODEL": "laya:latest",
        "LAYA_SIGNAL_FILTER_ENABLED": "true",
        "LAYA_DECISION_TIMEOUT_MS": "500",
        "DECAY_HALF_LIFE_DAYS": "30.0",
        "WORKING_MEMORY_MAX_TOKENS": "2000",
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

### 2.5 Restricting Admin Tools in `mcp.json` (Optional)
If your MCP client supports tool-level filtering (such as Cursor, Cline, or Windsurf), you can disable admin/maintenance tools so runtime agents only see the core agent tools:

```json
{
  "mcpServers": {
    "strata-memory": {
      "command": "/Users/dheeban/Documents/my_projects/ai-engineering-lab/strata-memory/.venv/bin/strata-mcp",
      "args": ["--transport", "stdio"],
      "disabledTools": [
        "memory_prune",
        "memory_purge_namespace"
      ],
      "autoApprove": [
        "memory_recall",
        "memory_ingest",
        "memory_edit",
        "memory_feedback"
      ]
    }
  }
}
```
*(For programmatic clients like LangChain `MultiServerMCPClient`, filter the returned tool list to `{"memory_recall", "memory_ingest", "memory_edit", "memory_feedback"}` before binding to your agent.)*

---

## 3. REST HTTP API via `curl` or HTTP Clients

Start the REST API daemon:
```bash
strata-api
```
Interactive OpenAPI Swagger UI is available at `http://localhost:8080/docs`.

### 3.1 `POST /v1/memory/ingest` (Laya Decision + Small LLM)
```bash
curl -X POST "http://localhost:8080/v1/memory/ingest" \
     -H "Content-Type: application/json" \
     -d '{
       "raw_text": "Dheeban founded the Velora project using Neon for persistent memory.",
       "namespace": "production",
       "fast_mode": false,
       "use_decision_model": true
     }'
```

### 3.2 `POST /v1/memory/recall` (Zero-LLM Hybrid Recall)
```bash
curl -X POST "http://localhost:8080/v1/memory/recall" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What project did Dheeban build and what database does it use?",
       "namespace": "production",
       "top_k": 5,
       "token_budget": 1500,
       "min_score": 0.0,
       "match_threshold": 0.35,
       "similarity_threshold": 0.40
     }'
```

### 3.3 `POST /v1/memory/store` (Direct Structured Write)
```bash
curl -X POST "http://localhost:8080/v1/memory/store" \
     -H "Content-Type: application/json" \
     -d '{
       "pillar": "semantic",
       "namespace": "production",
       "payload": {
         "summary": "Agent runtime is Python 3.14 on macOS arm64.",
         "tags": ["runtime", "python"]
       }
     }'
```

### 3.4 `POST /v1/memory/feedback` (Utility Reinforcement & Runbook Repair)
```bash
curl -X POST "http://localhost:8080/v1/memory/feedback" \
     -H "Content-Type: application/json" \
     -d '{
       "procedure_name": "deploy_neon_service",
       "success": false,
       "failure_reason": "asyncpg prepared statement collision on -pooler endpoint. statement_cache_size must be 0.",
       "namespace": "production"
     }'
```

### 3.5 `POST /v1/memory/edit` (Natural Language Modification)
```bash
curl -X POST "http://localhost:8080/v1/memory/edit" \
     -H "Content-Type: application/json" \
     -d '{
       "target_id_or_name": "deploy_neon_service",
       "instruction": "Add a step to verify pgvector extension after migration.",
       "pillar": "procedural",
       "namespace": "production"
     }'
```

### 3.6 `POST /v1/memory/delete` (Soft / Hard Deletion)
```bash
curl -X POST "http://localhost:8080/v1/memory/delete" \
     -H "Content-Type: application/json" \
     -d '{
       "target_id": "<UUID-OR-NAME>",
       "pillar": "semantic",
       "hard_delete": false,
       "namespace": "production"
     }'
```

### 3.7 Working Context Buffer & Tool Pinning (`/v1/working-memory/*`)

Record a tool output with protected status to prevent Eviction Policy Bug:
```bash
curl -X POST "http://localhost:8080/v1/working-memory/tool-output" \
     -H "Content-Type: application/json" \
     -d '{
       "session_id": "sess_agent_123",
       "tool_call_id": "call_status_456",
       "tool_name": "check_cluster_health",
       "content": "STATUS=HEALTHY, REGION=us-east-1, NODES=8",
       "namespace": "production",
       "protected": true
     }'
```

Retrieve active working context with token budget enforcement (never evicts protected tool outputs):
```bash
curl -X GET "http://localhost:8080/v1/working-memory/production/sess_agent_123?max_tokens=1000"
```

Unprotect a tool output once dependent downstream reasoning completes:
```bash
curl -X POST "http://localhost:8080/v1/working-memory/unprotect" \
     -H "Content-Type: application/json" \
     -d '{
       "session_id": "sess_agent_123",
       "tool_call_id": "call_status_456",
       "namespace": "production"
     }'
```

---

## 4. Popular Agent Framework Integrations

### 4.1 LangGraph / LangChain Python Agent
```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

async def create_strata_agent():
    # 1. Connect to Strata FastMCP Server
    client = MultiServerMCPClient({
        "strata": {
            "command": "/path/to/strata-memory/.venv/bin/strata-mcp",
            "args": ["--transport", "stdio"],
            "transport": "stdio",
        }
    })
    tools = await client.get_tools()

    # 2. Attach tools to caller LLM
    model = ChatOpenAI(model="gpt-4o")
    agent = create_react_agent(model, tools)
    return agent
```

### 4.2 CrewAI Integration
```python
from crewai import Agent
from crewai.tools import tool
from strata.service import svc_memory_recall, svc_memory_ingest

@tool("Recall Long-Term Memory")
def recall_memory(query: str) -> str:
    """Retrieve active memories from Strata."""
    import asyncio
    res = asyncio.run(svc_memory_recall(query=query))
    return res.formatted_context

developer_agent = Agent(
    role="Lead Systems Engineer",
    goal="Design scalable architectures grounded in historical project memory",
    tools=[recall_memory],
    backstory="You have access to Strata 4-pillar memory to maintain state across sessions.",
)
```

---

## 5. The MCP Protocol Handshake & Tool Specification

When an agent connects to Strata via MCP, it executes the `tools/list` handshake automatically. FastMCP inspects Python type hints and generates standard JSON Schema:

### Auto-Generated Schema Example (`memory_recall`)
```json
{
  "name": "memory_recall",
  "description": "Retrieve relevant memories across the 4 Cognitive Memory Pillars (<15ms, Zero-LLM).",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Natural language search query"
      },
      "namespace": {
        "type": "string",
        "default": "default"
      },
      "pillars": {
        "type": "array",
        "items": {
          "type": "string",
          "enum": ["semantic", "episodic", "procedural", "entity"]
        },
        "default": null
      },
      "top_k": {
        "type": "integer",
        "default": 5
      },
      "token_budget": {
        "type": "integer",
        "default": 1500
      },
      "match_threshold": {
        "type": "number",
        "default": null
      },
      "min_score": {
        "type": "number",
        "default": null
      },
      "similarity_threshold": {
        "type": "number",
        "default": null
      }
    },
    "required": ["query"]
  }
}
```

---

## 6. Agent Tool Exposure & System Prompt Guide

While the MCP JSON Schema tells the LLM **syntactically how** to construct tool calls, you should also restrict which tools are exposed to runtime agents and define **each tool's sole purpose and exact trigger event** in the **System Prompt**.

### 6.1 Recommended Tool Exposure Matrix

Expose only the **Agent Runtime Tools** to conversational/task agents; keep **Admin / Maintenance Tools** restricted to operator or scheduled-maintenance workflows.

| Exposure | Tool | Sole Purpose | Event / When to Use |
|---|---|---|---|
| **Expose to Agents** | `memory_recall` | Retrieve active context across the 4 pillars within a token budget. | Before answering user/project questions or starting a task that depends on prior context. |
| **Expose to Agents** | `memory_ingest` | Autonomously extract, route across pillars, and supersede conflicting facts from raw text. | Whenever the user shares new facts, role/config changes, preferences, events, or entity relations. |
| **Expose to Agents** | `memory_edit` | Modify a known `semantic` (by UUID) or `procedural` (by name/ID) record. | When making a targeted edit to a specific known record. *(Prefer `memory_ingest` for entity restructuring; `episodic` is immutable.)* |
| **Expose to Agents** | `memory_feedback` | Adjust `utility_score` (`+1` / `-2`) and auto-patch failed procedures. | Immediately after a task or runbook succeeds or fails using recalled memories. |
| **Expose (Optional)** | `memory_delete` | Soft-invalidate or permanently remove a single record by ID. | Only when explicitly asked to forget or delete a specific erroneous record. |
| **Expose (Optional)** | `memory_store_explicit` | Zero-LLM direct write when pillar and schema are already known. | Programmatic/structured pipelines (not typical natural-language turns). |
| **Admin Only** | `memory_prune` | Retire toxic memories, distill expiring episodes into reusable facts/runbooks, and purge old rows. | Manual admin cleanup or scheduled maintenance jobs. |
| **Admin Only** | `memory_purge_namespace` | Delete all records in a namespace. | Test teardown or explicit tenant deletion only. |

### 6.2 Agent System Prompt Snippet

Add this concise snippet to your agent's system prompt (e.g. your personal Jarvis agent):

```markdown
### Long-Term Memory (Strata Cognitive Memory Engine)
You are equipped with Strata, a 4-pillar long-term memory engine backed by Neon PostgreSQL.

1. RECALL (Before Answering):
   - Event: Before answering technical questions, architectural designs, code modifications, or past events.
   - Action: Invoke `memory_recall(query="...")` to retrieve `<strata_memory_context>` and ground your response.

2. INGEST (When Learning or Updating Information):
   - Event: When the user shares a new decision, preference, role/state change, event, or entity relationship.
   - Action: Invoke `memory_ingest(raw_text="...")` with natural language. Strata's Laya Decision Engine and Small LLM automatically extract facts, route across pillars, and supersede stale records.

3. EDIT (Targeted Revision of a Known Record):
   - Event: When you already have the target UUID or procedure name and need to apply a specific correction.
   - Action: Invoke `memory_edit(target_id_or_name="...", instruction="...", pillar="semantic|procedural")`. (Use `memory_ingest` to restructure entity relationships; `episodic` logs are immutable.)

4. FEEDBACK & SELF-HEALING (After Executing Tasks):
   - Event: Immediately after completing or failing a task/runbook that used recalled memories.
   - Action:
     - Success: Call `memory_feedback(memory_ids_used=[...], procedure_name="...", success=true)`.
     - Failure: Call `memory_feedback(memory_ids_used=[...], procedure_name="...", success=false, failure_reason="<exact error trace>")` so Strata can penalize bad memories and auto-patch the procedure steps.
```

---

## 7. Testing, Evaluation & Debugging Toolkit

### 7.1 Interactive CLI Demo
Validate the end-to-end memory lifecycle locally:
```bash
python examples/demo.py
```

### 7.2 End-to-End Evaluation Pipeline
Run the full 4-case evaluation suite against live Neon Postgres and Ollama:
```bash
python tests/eval_pipeline.py
```
This tests:
- Case 1: Autonomous Ingest & Entity Graph Extraction
- Case 2: Contradiction Detection & Automatic Superseding (via Laya)
- Case 3: Zero-LLM Fast Recall (<15ms)
- Case 4: Procedural Runbook Self-Healing

### 7.3 Direct Database Auditing via `psql`
Inspect raw records directly in your Neon console:
```sql
-- Check currently active semantic facts
SELECT memory_id, summary, tags, valid_from 
FROM memories 
WHERE namespace = 'default' AND type = 'semantic' AND valid_until IS NULL;

-- View audit trail of superseded facts
SELECT memory_id, summary, valid_from, valid_until, superseded_by 
FROM memories 
WHERE namespace = 'default' AND valid_until IS NOT NULL 
ORDER BY valid_until DESC;

-- View versioned procedural runbooks and changelog
SELECT name, version, steps, changelog, success_count, fail_count 
FROM procedural_memories 
WHERE namespace = 'default';

-- Inspect active knowledge graph edges
SELECT src.name AS source, e.relation_type, tgt.name AS target, e.fact_summary
FROM entity_edges e
JOIN entity_nodes src ON e.source_entity_id = src.entity_id
JOIN entity_nodes tgt ON e.target_entity_id = tgt.entity_id
WHERE e.namespace = 'default' AND e.valid_until IS NULL;
```
