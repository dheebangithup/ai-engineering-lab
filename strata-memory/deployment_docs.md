Analyzed DEPLOYMENT.md:L1-65
Edited DEPLOYMENT.md
Ran rsync updated docs/DEPLOYMENT.md to Instabox

I have created and documented the complete, production-grade **Manual & Template Deployment Guide** in [docs/DEPLOYMENT.md](file:///Users/dheeban/Documents/my_projects/ai-engineering-lab/strata-memory/docs/DEPLOYMENT.md) (and synced it directly to your Instabox server).

---

### Quick Summary of What’s Documented:

1. **System & Sizing Requirements**:
   - Minimum CPU, RAM, and Disk specifications for both Neon and local Docker setups.
   - Storage preparation (how to relocate Docker data root to `/data` if a cloud template has a small root `/` partition).

2. **The 3 Architecture Topologies**:
   - **Topology 1 (Recommended)**: Neon Serverless Postgres + Dockerized Ollama (`docker-compose.neon.yml`).
   - **Topology 2 (100% Offline)**: `pgvector` container + Dockerized Ollama (`docker-compose.yml`).
   - **Topology 3 (Apple Silicon / Dedicated GPU)**: Neon DB + Host Ollama (`docker-compose.external.yml`).

3. **Step-by-Step Manual Commands (No script magic)**:
   - Installing Docker & Compose.
   - Copy-paste `.env` templates for each topology (with clean environment variables, zero hardcoding).
   - How to build and launch using raw `docker compose` commands.
   - Applying SQL migrations manually via `psql` or automatically via `AUTO_MIGRATE=true`.

4. **Production Readiness & Probes**:
   - Verifying `/health` (liveness probe).
   - Verifying `/ready` (validates database readiness + Ollama model loading).
   - Testing Bearer auth on `/mcp`.

5. **Public SSL Ingress Options**:
   - Caddy Reverse Proxy (with automated Let's Encrypt SSL config).
   - Cloudflare Tunnels (zero port-forwarding).
   - Instabox Port Publishing.

6. **Agent Client Snippets**:
   - JSON configurations for Antigravity, Cursor, and Claude Desktop.

7. **Maintenance & Day-2 Operations**:
   - Viewing container logs, graceful restarts, and zero-downtime rolling rebuilds on code updates.