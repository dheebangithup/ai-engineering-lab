# Agent Integration & MCP Tool Discovery Guide

This document explains **how external agents discover, understand, and use Strata's MCP tools**, including both the underlying protocol handshake (JSON Schema) and the recommended agent prompt guidelines.

---

## 1. How the Agent Learns the Tool Specification (The MCP Protocol Handshake)

When you connect Strata to any agentic harness (Claude Desktop, Cursor, LangGraph, CrewAI, AutoGen, or custom agents), you **do not need to write custom JSON schema definitions by hand**.

The discovery happens automatically via the **Model Context Protocol (MCP)** specification:

```
[Agent Harness / IDE]                                                [Strata FastMCP Server]
         │                                                                      │
         │  1. JSON-RPC Handshake: `tools/list`                                 │
         ├─────────────────────────────────────────────────────────────────────►│
         │                                                                      │
         │  2. Returns Auto-Generated JSON Schema for all 6 tools               │
         │◄─────────────────────────────────────────────────────────────────────┤
         │                                                                      │
         │  3. Agent Harness injects schemas into LLM `tools` parameter         │
         │                                                                      │
         ▼                                                                      ▼
  [Caller LLM (Claude, GPT-4, Qwen)]
  Reads tool descriptions, allowed enum values, parameter types, and defaults.
```

---

## 2. Auto-Generated JSON Schemas (Live Example)

FastMCP inspects the Python type hints, docstrings, and Pydantic models in `src/strata/mcp_server.py` and compiles them into standard JSON Schema:

### Example A: `memory_recall`
```json
{
  "name": "memory_recall",
  "description": "Deterministic, zero-LLM recall across requested memory pillars (<15ms). Returns structured results and a pre-formatted XML context block bounded by token_budget.",
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
      }
    },
    "required": ["query"]
  }
}
```
*How the LLM understands it:* The LLM sees that `query` is required, `pillars` allows only four specific strings, and `token_budget` defaults to 1500.

---

### Example B: `memory_store_explicit`
```json
{
  "name": "memory_store_explicit",
  "description": "Direct, zero-LLM structured write to any of the 4 pillars when the agent has already structured the data.",
  "input_schema": {
    "type": "object",
    "properties": {
      "pillar": {
        "type": "string",
        "enum": ["semantic", "episodic", "procedural", "entity"]
      },
      "payload": {
        "type": "object"
      },
      "namespace": {
        "type": "string",
        "default": "default"
      }
    },
    "required": ["pillar", "payload"]
  }
}
```

---

## 3. Guiding the Agent on "When" and "Why" to Call Strata

While the MCP JSON Schema tells the LLM **syntactically how** to construct tool calls, the agent needs a short instruction in its **System Prompt** so it knows **when and why** to invoke memory.

Add this concise snippet to your agent's system prompt:

```markdown
### Long-Term Memory (Strata Cognitive Memory Engine)
You are equipped with Strata, a 4-pillar long-term memory engine backed by Neon PostgreSQL.

1. RECALL (Before Answering):
   - Before answering questions about project architecture, user preferences, technical decisions, or past procedures, call `memory_recall(query="...")`.
   - The tool will return a `<strata_memory_context>` XML block containing active facts, procedural skills, and entity graphs. Use these memories to ground your response.

2. INGEST (When Learning New Information):
   - When the user shares a new architectural decision, preference, or project fact, call `memory_ingest(raw_text="...")`.
   - Do NOT try to structure JSON yourself; Strata's internal decision router automatically extracts facts, detects contradictions, supersedes stale records, and maps entity relations.

3. FEEDBACK & SELF-HEALING (After Executing Tasks):
   - After executing a procedural runbook or skill:
     - If the task succeeded: Call `memory_feedback(procedure_name="...", success=true)`.
     - If the task failed: Call `memory_feedback(procedure_name="...", success=false, failure_reason="<exact error trace>")`. Strata will automatically analyze the failure and patch the runbook steps for future executions.
```

---

## 4. Connecting Strata to Popular Agent Frameworks

### A. Claude Desktop
Add to `claude_desktop_config.json`:
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

### B. Cursor IDE
In Cursor **Settings > Features > MCP**:
- Click **"Add New MCP Server"**
- Name: `strata-memory`
- Type: `command`
- Command: `/Users/dheeban/Documents/my_projects/ai-engineering-lab/strata-memory/.venv/bin/strata-mcp --transport stdio`

### C. LangChain / LangGraph Python Agent
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

    # 2. Attach tools to model
    model = ChatOpenAI(model="gpt-4o")
    agent = create_react_agent(model, tools)
    return agent
```

---

## 5. Summary: Two Halves of Agent Knowledge

| Aspect | Mechanism | How It Works |
|---|---|---|
| **Syntax & Types** | **MCP Protocol (`tools/list`)** | FastMCP publishes the machine-readable JSON Schema (types, parameters, defaults, enums) automatically on connection. |
| **Strategy & Workflow** | **System Prompt Guideline** | A simple 3-rule system prompt tells the LLM *when* to recall, *when* to ingest, and *when* to report feedback. |
