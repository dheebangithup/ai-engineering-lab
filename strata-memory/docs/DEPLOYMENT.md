# Strata Memory Engine — Production & Manual Deployment Guide

This document is the definitive guide for deploying **Strata Memory** as a high-performance, Streamable HTTP MCP server on any Linux server, cloud VM (AWS, GCP, DigitalOcean, Hetzner, Instabox), or local machine.

---

## 1. System Requirements & Architecture

### Recommended Server Specs
* **CPU**: 4 vCPU or higher (for fast vector search & small model inference)
* **RAM**: 
  * **When using Neon PostgreSQL**: 4 GB RAM minimum (Ollama takes ~2.5 GB for `qwen2.5:3b-instruct` + embeddings).
  * **When using Local Docker PostgreSQL**: 8 GB RAM minimum.
* **Disk**: 20 GB+ free disk space (to store model weights and container images).

### Runtime Dependencies
| Component | Necessity | Purpose |
| :--- | :---: | :--- |
| **PostgreSQL + `pgvector`** | **Required** | Bi-temporal memory storage, HNSW vector indexing, BM25 text search, entity graph relationships, and procedural versioning. Either **Neon Serverless Postgres** (recommended) or `pgvector/pgvector:pg16`. |
| **Ollama: `nomic-embed-text`** | **Required** (~274 MB) | Generates 768-dimension embeddings for every memory ingest and recall query. |
| **Ollama: `qwen2.5:3b-instruct`** | **Required** (~1.9 GB) | Autonomous 4-pillar extraction, functional-slot superseding, state evolutions, and episodic summaries. |

---

## 2. Choosing Your Deployment Topology

Strata Memory supports three distinct topologies:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ TOPOLOGY 1: Neon Cloud DB + Dockerized Ollama (RECOMMENDED FOR VM / TEMPLATES)          │
│ • Database: Neon Serverless Postgres (Zero VM RAM overhead, resilient to VM resets)     │
│ • Ollama: Docker container inside VM (models stored on persistent disk)                │
│ • MCP Server: Docker container inside VM                                               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ TOPOLOGY 2: 100% Self-Contained Local Stack (AIR-GAPPED / NO CLOUD DEPENDENCIES)       │
│ • Database: Dockerized pgvector/pgvector:pg16                                           │
│ • Ollama: Docker container inside VM                                                   │
│ • MCP Server: Docker container inside VM                                               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ TOPOLOGY 3: Cloud DB (Neon) + Host / Dedicated Ollama (APPLE SILICON METAL GPU)        │
│ • Database: Neon Serverless Postgres                                                   │
│ • Ollama: Running natively on host (for Apple Silicon Metal GPU or external GPU node)  │
│ • MCP Server: Docker container pointing to host.docker.internal                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Step-by-Step Manual Deployment

Follow these steps to deploy manually from scratch on any clean Linux machine.

### Step 1: Install Docker & Docker Compose
Ensure Docker and Docker Compose v2 are installed:
```bash
sudo apt-get update && sudo apt-get install -y curl git
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and log back in, or run: newgrp docker
docker compose version
```

> [!TIP]
> **Cloud VMs with Small Root Disks (`/` < 15 GB):**
> If your root partition is small but you have a larger secondary mount (e.g. `/data` or `/mnt`), move Docker's storage root to prevent disk exhaustion:
> ```bash
> sudo mkdir -p /data/docker /data/containerd
> sudo tee /etc/docker/daemon.json <<EOF
> {
>   "data-root": "/data/docker"
> }
> EOF
> sudo systemctl restart docker
> ```

---

### Step 2: Clone or Copy the Repository
```bash
git clone <your-repo-url> /data/workspace/strata-memory
cd /data/workspace/strata-memory
```

---

### Step 3: Create the Environment Configuration (`.env`)
Create `.env` based on your chosen topology. **Never commit `.env` to git.**

#### For Topology 1: Neon Serverless Postgres + Dockerized Ollama (Recommended)
```bash
cat << 'EOF' > .env
# Neon Database Connection Strings
DATABASE_URL="postgresql://neondb_owner:<password>@ep-<endpoint-id>-pooler.<region>.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
DIRECT_DATABASE_URL="postgresql://neondb_owner:<password>@ep-<endpoint-id>.<region>.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
DB_STATEMENT_CACHE_SIZE=0
DB_POOL_MIN_SIZE=1
DB_POOL_MAX_SIZE=10

# Optional: Neon Management API (auto-suspends compute when idle to save hours)
NEON_KEEP_ALIVE=false
NEON_API_KEY="napi_..."
NEON_PROJECT_ID="your-project-id"
NEON_ENDPOINT_ID="ep-endpoint-id"

# Embedding Configuration
EMBEDDING_PROVIDER="ollama"
EMBEDDING_BASE_URL="http://ollama:11434/v1"
EMBEDDING_API_KEY="ollama"
EMBEDDING_MODEL_NAME="nomic-embed-text"
EMBEDDING_DIMENSIONS=768

# Cognitive Extraction LLM Configuration
MEMORY_LLM_ENABLED=true
MEMORY_LLM_BASE_URL="http://ollama:11434/v1"
MEMORY_LLM_API_KEY="ollama"
MEMORY_LLM_MODEL="qwen2.5:3b-instruct"
MEMORY_LLM_TIMEOUT_SECONDS=120.0

# Server & MCP Configuration
AUTO_MIGRATE=true
MCP_TRANSPORT="streamable-http"
MCP_HOST="0.0.0.0"
MCP_PORT=8000
MCP_PATH="/mcp"
MCP_STATELESS_HTTP=true

# Security: Generate a secret bearer token: openssl rand -base64 24
MCP_AUTH_TOKEN="your-secure-random-token"
EOF
```

#### For Topology 2: Complete Local Stack (Local PostgreSQL container)
```bash
cat << 'EOF' > .env
POSTGRES_DB=strata
POSTGRES_USER=strata_user
POSTGRES_PASSWORD=strata_password
DATABASE_URL="postgresql://strata_user:strata_password@postgres:5432/strata"
DIRECT_DATABASE_URL="postgresql://strata_user:strata_password@postgres:5432/strata"
DB_STATEMENT_CACHE_SIZE=0
NEON_KEEP_ALIVE=true

EMBEDDING_PROVIDER="ollama"
EMBEDDING_BASE_URL="http://ollama:11434/v1"
EMBEDDING_API_KEY="ollama"
EMBEDDING_MODEL_NAME="nomic-embed-text"
EMBEDDING_DIMENSIONS=768

MEMORY_LLM_ENABLED=true
MEMORY_LLM_BASE_URL="http://ollama:11434/v1"
MEMORY_LLM_API_KEY="ollama"
MEMORY_LLM_MODEL="qwen2.5:3b-instruct"
MEMORY_LLM_TIMEOUT_SECONDS=120.0

AUTO_MIGRATE=true
MCP_TRANSPORT="streamable-http"
MCP_HOST="0.0.0.0"
MCP_PORT=8000
MCP_PATH="/mcp"
MCP_STATELESS_HTTP=true
MCP_AUTH_TOKEN="your-secure-random-token"
EOF
```

---

### Step 4: Launch the Containers

You can launch using the automated script or direct Docker commands:

* **Using Single-Click Helper (`deploy.sh`)**:
  ```bash
  # For Topology 1 (Neon DB):
  ./deploy.sh --neon

  # For Topology 2 (Full Local):
  ./deploy.sh

  # For Topology 3 (External DB & Host Ollama):
  ./deploy.sh --external
  ```

* **Or Using Raw Docker Compose Commands**:
  ```bash
  # For Topology 1 (Neon DB):
  docker compose -f docker-compose.neon.yml up -d --build

  # For Topology 2 (Full Local):
  docker compose up -d --build

  # For Topology 3 (External):
  docker compose -f docker-compose.external.yml up -d --build
  ```

During startup:
1. Docker builds the lightweight `strata-mcp` Python wheel image.
2. `strata-ollama-init` pulls `nomic-embed-text` and `qwen2.5:3b-instruct` into the persistent volume `strata_ollama_data`.
3. `strata-mcp`'s startup hook connects to the database, applies `sql/001_init_schema.sql` (if `AUTO_MIGRATE=true`), and begins listening on port `8000`.

---

### Step 5: Verify Server Health & Readiness

Check that the server is online and all sub-systems are healthy:

```bash
# 1. Check running containers
docker ps

# 2. Check Liveness (returns 200 OK without requiring auth)
curl -s http://localhost:8000/health
# Response: {"status":"ok","engine":"strata-memory","version":"0.1.0"}

# 3. Check Readiness (verifies DB connection + Ollama models)
curl -s http://localhost:8000/ready
# Response: {"status":"ready","checks":{"postgres":"ok","embedding_service":"ok","loaded_models":["qwen2.5:3b-instruct","nomic-embed-text:latest"]}}

# 4. Verify Auth Protection on /mcp (should return 401 without token)
curl -i http://localhost:8000/mcp
# Response: HTTP 401 Unauthorized

# 5. Check Web UI Dashboard & REST API
curl -s http://localhost:8000/
# Response: Strata Memory Studio HTML

curl -s http://localhost:8000/v1/ui/stats
# Response: {"namespaces":["default",...],"semantic":{"active":...}}
```

---

## 4. Public Internet Exposure & SSL

To connect AI clients (Cursor, Claude, Antigravity) running on other machines, expose port `8000` via HTTPS.

### Option A: Using Caddy (Easiest with Auto-SSL)
Install Caddy:
```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLF 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLF 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy
```
Create `/etc/caddy/Caddyfile`:
```caddy
memory.yourdomain.com {
    reverse_proxy localhost:8000 {
        # Allow long-lived SSE / Streamable HTTP MCP streams
        transport http {
            response_header_timeout 300s
        }
    }
}
```
Reload Caddy:
```bash
sudo systemctl reload caddy
```

### Option B: Using Cloudflare Tunnel (Zero Port-Forwarding Needed)
```bash
cloudflared tunnel create strata-memory
cloudflared tunnel route dns strata-memory memory.yourdomain.com
cloudflared tunnel run --url http://localhost:8000 strata-memory
```

### Option C: In Instabox / Ephemeral Sandboxes
```bash
instabox-port publish 8000
# Returns: https://8000-<machine-id>.instabox.tech
```

---

## 5. Client Configuration (Antigravity / Cursor / Claude)

Add this configuration snippet to your agent's MCP settings:

```json
{
  "mcpServers": {
    "strata-memory": {
      "url": "https://<your-domain-or-proxy-url>/mcp",
      "headers": {
        "Authorization": "Bearer <your-mcp-auth-token>"
      }
    }
  }
}
```

---

## 6. Maintenance & Troubleshooting

### Inspecting Logs
```bash
# View MCP server logs
docker compose logs -f strata-mcp

# View Ollama logs
docker compose logs -f ollama
```

### Restarting the Services
```bash
# Graceful restart
docker compose -f docker-compose.neon.yml restart strata-mcp

# Full teardown and restart
docker compose -f docker-compose.neon.yml down
docker compose -f docker-compose.neon.yml up -d
```

### Updating to a New Version
```bash
git pull origin main
docker compose -f docker-compose.neon.yml up -d --build strata-mcp
```

### Database Schema Upgrades
If a new SQL migration is added under `sql/`:
- With `AUTO_MIGRATE=true`, `strata-mcp` applies migrations on boot automatically.
- To execute manually using `psql`:
  ```bash
  psql "$DIRECT_DATABASE_URL" -f sql/001_init_schema.sql
  ```
