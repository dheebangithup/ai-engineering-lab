# Strata Memory Engine — Production Deployment Guide

## 1. Runtime Dependencies Overview

| Component | Requirement | Purpose |
| :--- | :--- | :--- |
| **PostgreSQL + `pgvector`** | **Required** | Bi-temporal semantic/episodic storage, HNSW vector search, BM25 FTS, procedural versioning, and entity graph. Bundled as `pgvector/pgvector:pg16` or external **Neon Serverless Postgres**. |
| **Ollama + `nomic-embed-text`** | **Required** (~274 MB) | Generates 768-dimension embeddings for every ingest and recall. |
| **Ollama + `qwen2.5:3b-instruct`** (or `qwen3:8b`) | **Required when `MEMORY_LLM_ENABLED=true`** | Autonomous 4-pillar extraction, functional-slot superseding, intelligent edit rewrites, and episodic distillation. |

> **Note:** `laya:latest` is **not** required; the Laya decision engine operates purely in-memory (`<0.2ms`) and delegates overlapping/complex inputs to `MEMORY_LLM_MODEL`.

---

## 2. Single-Click Deployment Options

### Option A: Complete Self-Contained Local / Linux VPS Stack
Includes `postgres` (`pgvector`), `ollama`, automatic model pulling (`ollama-init`), and the Streamable HTTP MCP server (`strata-mcp` on port `8000`):

```bash
./deploy.sh
# or directly:
docker compose up -d --build
```

### Option B: Cloud DB (Neon) + Host Ollama (Recommended for macOS Apple Silicon)
On macOS, Docker Linux VMs cannot access Apple Metal GPU, so running Ollama natively on the host (`ollama serve`) and pointing Dockerized `strata-mcp` at `host.docker.internal:11434` plus external Neon PostgreSQL gives full Metal GPU speed:

1. Configure `DATABASE_URL` and `DIRECT_DATABASE_URL` in `.env` (pointing to Neon).
2. Ensure Ollama is running on host with `nomic-embed-text` and your LLM pulled:
   ```bash
   ollama pull nomic-embed-text
   ollama pull qwen2.5:3b-instruct
   ```
3. Launch with one command:
   ```bash
   ./deploy.sh --external
   # or:
   docker compose -f docker-compose.external.yml up -d --build
   ```

---

## 3. Endpoints & Security

* **Streamable HTTP MCP Endpoint**: `http://<host>:8000/mcp`
* **Liveness Probe**: `GET http://<host>:8000/health` (always unauthenticated)
* **Readiness Probe**: `GET http://<host>:8000/ready` (verifies Postgres `SELECT 1` + Ollama model presence)
* **Bearer Authentication**: Set `MCP_AUTH_TOKEN="your-secret-token"` in `.env` to protect `/mcp` while keeping `/health` and `/ready` open for load balancers.

### Client Configuration (Antigravity / Cursor / Claude)

```json
{
  "mcpServers": {
    "strata-memory": {
      "serverUrl": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer your-secret-token-if-set"
      }
    }
  }
}
```
*(Omit `"headers"` if `MCP_AUTH_TOKEN` is unset.)*
