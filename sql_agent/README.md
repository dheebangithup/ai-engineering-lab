# 📊 SQL Analyst Agent

An AI-powered SQL data analyst agent built with **Claude** and the **Anthropic Python SDK**.

Ask natural language questions about your data — the agent automatically inspects the database schema, writes SQL queries, executes them, and summarizes the results. Now featuring a **premium real-time dashboard** to visualize the agent's internal reasoning.

## Features

- 🤖 **Claude-powered** — Uses Claude's tool-use capabilities via a modular **Skills** architecture
- ⚡ **Real-time Flow Visualizer** — See "behind-the-scenes" skill activation, tool calls, and executed SQL
- 🌐 **Premium Web UI** — Dark-themed FastAPI dashboard with SSE streaming
- 💬 **Conversation Memory** — Multi-turn context with session persistence to disk (`session.json`)
- 🛡️ **Safe by default** — Only `SELECT` queries allowed, dangerous keywords blocked
- ⚙️ **Configurable** — Model, tokens, DB path all via environment variables

## Quick Start

### 1. Install dependencies

```bash
cd sql_agent
uv sync
```

### 2. Set your API key

Create a `.env` file:

```env
ANTHROPIC_API_KEY=your-api-key-here
MODEL_NAME=claude-3-5-sonnet-20240620
```

### 3. Run the Dashboard (Recommended)

```bash
uv run main.py
```
Then visit `http://localhost:8000` in your browser.

## Configuration

All settings can be overridden via environment variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Your Anthropic API key (required) |
| `MODEL_NAME` | `claude-3-5-sonnet-20240620` | Claude model to use |
| `MAX_TOKENS` | `4096` | Max tokens per response |
| `DB_PATH` | `sales.db` | Path to SQLite database |
| `MAX_ROWS` | `1000` | Max rows returned per query |

## Architecture

```
sql_agent/
├── main.py           ← Unified entry point (FastAPI Dashboard)
├── config.py         ← Centralized configuration
├── agent/
│   └── skills_agent.py  ← Core agent with Skills logic & streaming
├── static/
│   ├── index.html    ← Premium Dashboard UI
│   └── style.css     ← UI styles (Glassmorphism, dark-mode)
├── core/
│   └── data_base_manager.py ← Database operations & safety
├── tools/            ← Specialized toolkits
│   ├── sql_tool.py
│   ├── export_tool.py
│   └── quality_tool.py
└── .claude/skills/   ← Domain-specific skill definitions
```

## Testing

Run the toolkit test (no API key needed):

```bash
uv run test_sql.py
```

## License

MIT
