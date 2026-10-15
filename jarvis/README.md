# J.A.R.V.I.S. — Tools Gateway MVP

A modular Tools Gateway for the J.A.R.V.I.S. AI agent, following the deferred tool discovery paradigm.

## Core Architecture

The Tools Gateway consists of three decoupled components:

1. **`ToolRegistry`** ([`tool_registry.py`](file:///Users/dheeban/Documents/my_projects/ai-engineering-lab/jarvis/src/jarvis/tools/tool_registry.py))
   - Stores tool definitions and their callable implementations in memory.
   - Prevents duplicate tool IDs (`DuplicateToolError`).
   - Exposes public `ToolDefinition` metadata without leaking Python implementation functions.

2. **`ToolDiscovery`** ([`tool_discovery.py`](file:///Users/dheeban/Documents/my_projects/ai-engineering-lab/jarvis/src/jarvis/tools/tool_discovery.py))
   - Accepts natural-language user requests.
   - Tokenizes and ranks registered tools using the **`rank-bm25`** library (`BM25Okapi` algorithm with $k_1=1.5, b=0.75, \epsilon=0.25$).
   - Returns only the matching `ToolDefinition` objects up to a configurable `max_results`.
   - Returns an empty list when no relevant tools match.

3. **`ToolsGateway`** ([`tools_gateway.py`](file:///Users/dheeban/Documents/my_projects/ai-engineering-lab/jarvis/src/jarvis/tools/tools_gateway.py))
   - The centralized execution entry point for all agent tool invocations.
   - Validates arguments against each tool's JSON-schema-compatible parameter specification.
   - Gracefully handles unknown tool IDs, schema violations, and execution failures.
   - Always returns a standardized [`ToolResult`](file:///Users/dheeban/Documents/my_projects/ai-engineering-lab/jarvis/src/jarvis/tools/schemas.py).

---

## Registered Initial Tools

Implemented in [`src/jarvis/tools/implementations/`](file:///Users/dheeban/Documents/my_projects/ai-engineering-lab/jarvis/src/jarvis/tools/implementations):

| Tool ID | Name | Description | Safeguard |
|---|---|---|---|
| `list_files` | List Files | List files/folders in an allowed directory | Restricted to base directory via `Path.resolve()` |
| `read_file` | Read File | Read text content from a file | Path traversal checks (`PathTraversalError`) |
| `write_file` | Write File | Write content to a file in workspace | Path traversal checks, parent dir creation |
| `search_files` | Search Files | Search files for a text pattern | Path traversal checks |
| `run_command` | Run Command | Execute permitted command | Explicit allowlist, `shell=False` (no injection) |

---

## Agent Workflow

```
1. User Request: "Find all Python files in the project"
                     │
                     ▼
2. ToolDiscovery: BM25 ranks tools against query tokens -> selects 'list_files'
                     │
                     ▼
3. Agent: Receives ToolDefinition and inspects JSON input schema
                     │
                     ▼
4. Agent: Supplies arguments {"directory": "src", "recursive": true}
                     │
                     ▼
5. ToolsGateway: Validates arguments against schema & executes implementation
                     │
                     ▼
6. ToolResult: Structured output {tool_id, success, data, error, metadata}
```

---

## Running the Demo

Execute the standalone demonstration script:

```bash
uv run python examples/demo_gateway.py
```

This runs both the agent workflow scenario as well as security and error-handling tests (path traversal protection, command allowlist rejection, schema validation, and unknown tool IDs).

---

## Running the Tests

Run the test suite with pytest:

```bash
# Run tool suite tests
uv run pytest tests/tools/ -v
```
