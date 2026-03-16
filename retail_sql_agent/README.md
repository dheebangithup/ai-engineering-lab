# 📊 SQL Analyst Agent

An AI-powered SQL data analyst agent fully built with the **Claude Agent SDK**.

Ask natural language questions about your data — the agent automatically inspects the database schema, writes SQL queries, executes them, and summarizes the results. Now featuring a **premium real-time dashboard** to visualize the agent's internal reasoning using the native SDK capabilities.

## Features

- 🤖 **Claude Agent SDK** — Uses the native SDK for tool-orchestration and Skills deployment
- ⚡ **Real-time Flow Visualizer** — See "behind-the-scenes" skill activation, tool calls, and executed SQL
- 🌐 **Premium Web UI** — Dark-themed FastAPI dashboard with SSE streaming
- 💬 **Conversation Memory** — SDK-native session resumption via `session_id` (Auto-saves context)
- 🛡️ **Safe by default** — Only `SELECT` queries allowed, dangerous keywords blocked via MCP
- 🗄️ **Multi-database Support** — Connects to PostgreSQL, MySQL, and SQLite out of the box (`sqlalchemy`)
- ⚙️ **Configurable** — Model, connection string, tokens all via environment variables

## Quick Start

### 1. Install dependencies

```bash
cd retail_sql_agent
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
| `DATABASE_URL` | `sqlite:///sales.db` | Connection string for SQLite, Postgres, MySQL |
| `MAX_ROWS` | `1000` | Max rows returned per query |

## Architecture

```
sql_agent/
├── main.py           ← Unified entry point (FastAPI Dashboard)
├── config.py         ← Centralized configuration (API keys, DB URLs)
├── agent/
│   └── retail_agent.py  ← Core agent with native SDK integration
├── static/
│   ├── index.html    ← Premium Dashboard UI
│   └── style.css     ← UI styles (Glassmorphism, dark-mode)
├── core/
│   └── database_manager.py ← Expanded schema & sample data
├── tools/            ← Specialized toolkit (MCP-based)
│   ├── export_tools.py
│   └── database_tools.py
├── tests/            ← Dedicated test scripts
│   ├── test_agent_sdk.py
│   ├── test_extended_db.py
│   └── test_sql.py
└── .claude/skills/   ← Domain-specific skill definitions (Optimized)
```
## Sample Queries

### 📈 Retail & Trend Analysis
- **Top performers:** "What were our top 3 best-selling products by revenue last month, and how do they compare?"
- **Sales patterns:** "Show me the daily sales trend for the past 14 days. Are there any noticeable spikes?"
- **Category performance:** "Which product category is our 'cash cow'? Give me a breakdown of revenue by category name."
- **Customer loyalty:** "Who are our top 3 customers by total spending, and how many loyalty points do they have?"

### 👔 Executive Business Intelligence (KPIs)
- **Business health:** "Give me an executive summary of our overall business health over the last 90 days."
- **AOV metrics:** "Calculate our Average Order Value (AOV) and total revenue for the current quarter."
- **Customer metrics:** "Which customers have joined in the last year and have over 400 loyalty points?"

### 🔮 Forecasting & Inventory Management
- **Stock warnings:** "Show me all products with a 'stock_level' below their 'reorder_point'. Which supplier should I contact for each?"
- **Inventory planning:** "Based on the sales velocity of 'Laptops', how many weeks of inventory do we have left?"
- **Sourcing:** "List all products supplied by 'Global Tech' and their current availability."

## Testing

Run the toolkit test (no API key needed):

```bash
uv run tests/test_sql.py
```

Run the full agent simulation (API key required):

```bash
uv run tests/test_agent_sdk.py
```

## License

MIT
