# 📊 Retail SQL Analyst Agent

An enterprise-ready SQL data analyst agent fully built with the **Claude Agent SDK**. 

Ask natural language questions about your retail data — the agent automatically inspects the database schema, writes optimized SQL, executes it, and provides business insights. Featuring a **premium multi-session dashboard** to visualize the agent's internal reasoning and history.

![Retail Agent Showcase](retail_agent.gif)

---

## 🌟 Key Highlights

- 🧠 **Claude Agent SDK Native** — Leverages the latest SDK for robust tool orchestration and modular Skills deployment.
- 🕒 **Multi-Session History** — ChatGPT-like sidebar to manage multiple analysis threads with **Manual Renaming** support (Auto-saved to `sessions.json`).
- ⚡ **Real-time Flow Visualizer** — Transparent "behind-the-scenes" view of skill activation, tool calls, and SQL generation.
- 💰 **Built for Scale & Savings** — Optimized for token efficiency via Skill-Layer Caching and Progressive Disclosure.
- 🛡️ **Safety-First Design** — Read-only SQL enforcement and dangerous keyword filtering via MCP server.

---

## 🚀 Why This Architecture? (Pros & Advantages)

| Aspect | Benefit | Why it matters |
|--------|---------|----------------|
| **Modular Skills** | Scalability | Add new domain knowledge (e.g., HR, Finance) by just dropping a new `SKILL.md` file. |
| **Skill-Layer Caching** | Speed & Cost | Primary schemas are embedded in skills, allowing for **one-turn query execution** (70% faster). |
| **Progressive Disclosure** | Token Efficiency | Only fetches schema details for relevant tables, preventing "context window pollution." |
| **Native Session Mgmt** | UX Consistency | SDK-native `session_id` integration ensures seamless history restoration across page refreshes. |
| **MCP Integration** | Interoperability | Easily connect to other tools and agents using the Model Context Protocol. |

---

## 📉 Context & Cost Management

This agent is designed to minimize Anthropic API costs while maximizing reasoning quality:

1.  **Zero-Query Discovery**: Standard tables (Sales, Inventory, Products) are pre-defined in skills. The agent writes SQL immediately without asking "What tables do you have?".
2.  **Fallback Discovery**: For complex discovery, it uses a two-step "Progressive Disclosure" (list tables -> fetch specific schema) to avoid dumping a 500-table schema into the prompt.
3.  **Result Pruning**: Large datasets are summarized by the tool before being sent to Claude, keeping the context window focused on the answer, not the raw data.

---

## 🛠️ Performance & Scalability

- **Database Agnostic**: Powered by `SQLAlchemy`, supports PostgreSQL, MySQL, and SQLite.
- **Concurrent-Ready**: Built on `FastAPI` and `AsyncIO` for high-performance streaming.
- **Persistent Storage**: Session history is stored locally in JSON format, ready for easy expansion to Redis or Postgres for larger scales.

---

## 📂 Architecture

```
retail_sql_agent/
├── main.py              ← FastAPI entry point & API endpoints
├── agent/
│   └── retail_agent.py  ← Core agent logic & SDK integration
├── core/
│   ├── database_manager.py ← Schema setup & sample data
│   └── session_manager.py  ← Persistent chat history logic
├── static/
│   ├── index.html       ← Premium Sidebar-based UI
│   └── style.css        ← Glassmorphism & premium aesthetics
├── .claude/skills/      ← Domain-specific optimized skills
└── tools/               ← Specialized MCP toolkit
```

---

## 🏁 Quick Start

1. **Install Dependencies**:
   ```bash
   uv sync
   ```

2. **Configure Environment**:
   Create a `.env` file with your `ANTHROPIC_API_KEY`.

3. **Launch Dashboard**:
   ```bash
   uv run main.py
   ```
   Visit `http://localhost:8000` to start analyzing.

---

## 🧪 Testing

- **Quick SQL Test**: `uv run tests/test_sql.py`
- **Agent Simulation**: `uv run tests/test_agent_sdk.py`
- **Schema Integrity**: `uv run tests/test_extended_db.py`

---

## 📜 License
MIT
