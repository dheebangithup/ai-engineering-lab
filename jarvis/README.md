# J.A.R.V.I.S. — Personal AI Agent & Engineering Partner

J.A.R.V.I.S. (Just A Rather Very Intelligent System) is a modular, personal AI agent system inspired by Iron Man's JARVIS. Built with runtime-composable architecture, multi-provider fault tolerance, sub-5ms decision routing, an Uber-scale deferred tools gateway with human-in-the-loop security, and Model Context Protocol (MCP) multi-server integration.

---

## 🌟 Key Architectural Pillars

### 1. Resilient Multi-Provider LLM Gateway
- Supports **Ollama Local**, **KodeKloud OpenAI-compatible**, **Groq**, and standard OpenAI endpoints.
- Dynamic fallback chains: automatically cascades to secondary/tertiary providers if the primary endpoint experiences network failure, 403 model restriction, or timeouts.
- Dynamic configuration store (`~/.jarvis/settings/providers.json`) allows adding, modifying, or re-ordering providers via the UI without application restarts.

### 2. Sub-5ms Decision Model
- Evaluates task complexity (`SIMPLE`, `MODERATE`, `COMPLEX`) and detects intent (`CONVERSATION`, `WEB_SEARCH`, `FILE_PROCESSING`, `CODE_DEV`, `SYSTEM_COMMAND`, `MEMORY_QUERY`, `PLANNING`).
- Uses zero-LLM fast path and deterministic classification models (<5ms) to route tasks without waking up heavy generative chat loops.

### 3. Tools Gateway (The Uber Pattern)
- Scales from 5 tools to 10,000+ tools seamlessly.
- Agents are exposed to **only 3 meta-tools**:
  1. `search_tools`: Discovers relevant tools dynamically using natural language BM25Okapi search.
  2. `list_tools`: Browses available tool categories.
  3. `execute_tool`: Validates schemas, enforces permissions, and executes sandboxed actions.
- **Human-in-the-Loop Security**:
  - `SAFE`: Read-only actions (auto-permitted).
  - `SENSITIVE`: State modifications (audited).
  - `DANGEROUS`: High-risk or destructive actions (e.g. `run_command`, `memory_delete`, `memory_prune`, `memory_purge_namespace`, `memory_edit`) require explicit authorization.

### 4. Strata Cognitive Memory via MCP Protocol
- Connects to the **Strata 4-Pillar Memory Engine** (`strata-mcp`) via the official Model Context Protocol (MCP) over `stdio`.
- **Zero modification to sibling project code**.
- Auto-bridges 8 cognitive memory tools (`memory_recall`, `memory_ingest`, `memory_store_explicit`, `memory_edit`, `memory_feedback`, `memory_delete`, `memory_prune`, `memory_purge_namespace`).

### 5. Single Source of Truth (SSOT) Workspace
- Fully configurable via `JARVIS_WORKSPACE` (default: `~/.jarvis`):
  ```
  ~/.jarvis/
  ├── settings/          # providers.json, mcp_servers.json, agent_config.json
  ├── memory/            # Local memory caches and audit trails
  ├── code_workspace/    # Isolated execution sandbox for coding agents
  ├── logs/              # app.log and jarvis.log
  └── storage/           # sessions.db
  ```
- Dynamic discovery of sibling repositories without hardcoded user paths.

---

## 🚀 Running the Web Application & UI

Launch the complete web application and modern React HUD dashboard:

```bash
./run.sh
```

Or manually:
```bash
uv run python app.py
```

Open your browser at **[http://localhost:8000](http://localhost:8000)**.

The React HUD Web UI (`frontend/`) features:
- **💬 Command Console**: Interactive chat with execution mode selector (Auto vs Direct Provider), real-time reasoning trace accordion, markdown formatting, and tool execution badges.
- **🤖 LLM Providers & Fallback**: Interactive Primary & Secondary fallback chain controls for each role (`fast`, `reasoning`, `decision`) with one-click save, live latency monitoring, edit provider capabilities, and dynamic endpoint configuration.
- **🔌 External MCP Servers**: Live status of connected MCP servers (`strata-memory`) and tool bridging.
- **🔧 Tools & Permissions**: Searchable and category-filtered explorer of registered tools and security authorization tiers.
- **📁 Workspace SSOT**: Visual layout and JSON viewer of the active workspace configuration.

---

### Frontend Development (Optional)
If modifying the React UI in `frontend/`:
```bash
cd frontend
npm run dev # Starts Vite dev server on http://localhost:3000 with API proxy to :8000
npm run build # Compiles production assets into frontend/dist
```

---

## 🖥️ Running the Interactive Terminal CLI

To chat with J.A.R.V.I.S. directly in your terminal with live authorization challenges:

```bash
uv run python -m jarvis.interfaces.cli
```

---

## 🧪 Running the Test Suite

Run all 35 unit and integration tests:

```bash
uv run pytest tests/ -v
```
