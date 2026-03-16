# 📊 SQL Analyst Agent

An AI-powered SQL data analyst agent fully built with the **Claude Agent SDK**.

Ask natural language questions about your data — the agent automatically inspects the database schema, writes SQL queries, executes them, and summarizes the results. Now featuring a **premium real-time dashboard** to visualize the agent's internal reasoning using the native SDK capabilities.

## Features

- 🤖 **Claude Agent SDK** — Uses the native SDK for tool-orchestration and Skills deployment
- ⚡ **Real-time Flow Visualizer** — See "behind-the-scenes" skill activation, tool calls, and executed SQL
- 🌐 **Premium Web UI** — Dark-themed FastAPI dashboard with SSE streaming
- 💬 **Conversation Memory** — Multi-turn context with session persistence to disk (`session.json`)
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
│   └── retail_agent.py  ← Core agent with Skills logic & streaming
├── static/
│   ├── index.html    ← Premium Dashboard UI
│   └── style.css     ← UI styles (Glassmorphism, dark-mode)
├── core/
│   └── database_manager.py ← Database operations & safety
├── tools/            ← Specialized toolkits
│   ├── export_tools.py
│   └── database_tools.py
└── .claude/skills/   ← Domain-specific skill definitions
```
## Sample Queries

### 📈 Retail & Trend Analysis
- **Top performers:** "What were our top 3 best-selling products by revenue last month, and how do they compare to the month prior?"
- **Sales patterns:** "Show me the daily sales trend for the past 14 days. Are there any noticeable spikes?"
- **Category analysis:** "Which product category is driving the most volume, but the least revenue?"
- **Inventory insights:** "Based on our sales data, which products are considered 'dead stock' (items that haven't sold at all recently)?"

### 👔 Executive Business Intelligence (KPIs)
- **Business health:** "Give me an executive summary of our overall business health over the last 90 days."
- **Revenue metrics:** "Calculate our Average Order Value (AOV) and total revenue for the current quarter."
- **Category performance:** "I need a breakdown of revenue contribution by category. Which category is our cash cow?"

### 🔮 Forecasting & Inventory Management
- **Inventory planning:** "Based on the average weekly sales velocity of 'Laptops', how many weeks of inventory do we have left?"
- **Revenue forecasting:** "Forecast our expected revenue for the next 7 days based on the daily average of the last 30 days."

## Testing

Run the toolkit test (no API key needed):

```bash
uv run test_sql.py
```

## License

MIT
