#!/usr/bin/env bash
set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

MODE="full"
if [[ "${1:-}" == "--external" ]]; then
  MODE="external"
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: Docker is not installed or not in PATH."
  exit 1
fi

if [ ! -f ".env" ]; then
  echo "No .env found; creating from .env.example..."
  cp .env.example .env
fi

echo "================================================================================"
echo "  Strata Memory - Single-Click HTTP Streamable MCP Deployment (mode: $MODE)"
echo "================================================================================"

if [[ "$MODE" == "external" ]]; then
  echo "Starting Strata MCP against external Neon DB / Host Ollama..."
  docker compose -f docker-compose.external.yml up -d --build
else
  echo "Starting full local stack (pgvector + Ollama + auto-model pull + Strata MCP)..."
  docker compose up -d --build
fi

PORT="${MCP_PORT:-8000}"
MCP_PATH_VAL="${MCP_PATH:-/mcp}"

echo "Waiting for Strata MCP readiness endpoint (http://localhost:${PORT}/ready)..."
for i in $(seq 1 40); do
  if curl -fsS "http://localhost:${PORT}/ready" >/dev/null 2>&1; then
    echo ""
    echo "================================================================================"
    echo "  DEPLOYMENT READY!"
    echo "  Streamable HTTP MCP URL : http://localhost:${PORT}${MCP_PATH_VAL}"
    echo "  Health Check            : http://localhost:${PORT}/health"
    echo "  Readiness Check         : http://localhost:${PORT}/ready"
    echo "================================================================================"
    echo ""
    echo "Client MCP JSON snippet:"
    cat <<EOF
{
  "mcpServers": {
    "strata-memory": {
      "serverUrl": "http://localhost:${PORT}${MCP_PATH_VAL}"
    }
  }
}
EOF
    exit 0
  fi
  sleep 3
done

echo "Warning: /ready did not report 200 within 120s. Check logs with:"
echo "  docker compose logs -f strata-mcp"
exit 1
