# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MCP_TRANSPORT=streamable-http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    MCP_PATH=/mcp \
    MCP_STATELESS_HTTP=true \
    AUTO_MIGRATE=true

WORKDIR /app

# Install minimal runtime tools (curl for container HEALTHCHECK)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy build metadata and source code
COPY pyproject.toml README.md ./
COPY sql ./sql
COPY src ./src

# Install package and runtime dependencies non-editably
RUN pip install --upgrade pip && pip install .

# Run as unprivileged user
RUN useradd --create-home --shell /bin/bash strata && chown -R strata:strata /app
USER strata

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${MCP_PORT}/health" || exit 1

CMD ["strata-mcp"]
