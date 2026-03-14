# 📊 SQL Analyst Agent

An AI-powered SQL data analyst agent built with **Claude** and the **Anthropic Python SDK**.

Ask natural language questions about your data — the agent automatically inspects the database schema, writes SQL queries, executes them, and summarizes the results.

## Features

- 🤖 **Claude-powered** — Uses Claude's tool-use capabilities via `@beta_tool` + `tool_runner`
- 🔧 **Auto tool orchestration** — SDK handles the agentic loop (schema → query → summarize)
- 💬 **Conversation memory** — Follow-up questions reference previous context
- 🛡️ **Safe by default** — Only `SELECT` queries allowed, dangerous keywords blocked
- ⚙️ **Configurable** — Model, tokens, DB path all via environment variables
- 🔄 **Error resilient** — Graceful handling of API errors, rate limits, and connection issues

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
```

### 3. Run the agent

```bash
uv run main.py
```

### 4. Ask questions

```
🔎 Ask a question: What are the top selling products?
🔎 Ask a question: Show revenue by category last 30 days
🔎 Ask a question: reset    ← clears conversation history
🔎 Ask a question: exit     ← quit
```

## Configuration

All settings can be overridden via environment variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Your Anthropic API key (required) |
| `MODEL_NAME` | `claude-sonnet-4-20250514` | Claude model to use |
| `MAX_TOKENS` | `4096` | Max tokens per response |
| `DB_PATH` | `sales.db` | Path to SQLite database |
| `MAX_ROWS` | `1000` | Max rows returned per query |

## Architecture

```
sql_agent/
├── main.py           ← CLI entry point
├── config.py         ← Centralized configuration
├── agent/
│   └── claude_agent.py  ← Agent using SDK's tool_runner
├── core/
│   └── data_base_manager.py  ← Database operations & safety
├── tools/
│   └── sql_tool.py   ← @beta_tool decorated functions
└── test_sql.py       ← Toolkit smoke test
```

### Key SDK Features Used

- **`@beta_tool`** — Decorator that auto-generates tool JSON schemas from Python function signatures and docstrings
- **`tool_runner`** — Handles the entire agentic loop automatically (no manual `while` loop needed)
- **Error classes** — `AuthenticationError`, `RateLimitError`, `APIConnectionError` for graceful failures
- **Retries & timeouts** — Built-in exponential backoff via `max_retries` config

## Testing

Run the toolkit test (no API key needed):

```bash
uv run test_sql.py
```

## License

MIT
