#!/usr/bin/env bash
set -e

# Determine directory of this script (project root)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Use virtual environment python
if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
else
    echo "⚠️ .venv not found, falling back to uv run..."
    PYTHON_BIN="uv run python"
fi

# Ensure React Frontend is built
if [ ! -f "$PROJECT_ROOT/frontend/dist/index.html" ]; then
    echo "📦 Building modern React HUD frontend..."
    (cd "$PROJECT_ROOT/frontend" && npm install && npm run build)
fi

echo "=============================================================="
echo " 🤖 Starting J.A.R.V.I.S. Web Application using .venv"
echo " 📁 Project Root: $PROJECT_ROOT"
echo " 🐍 Python Binary: $PYTHON_BIN"
echo " 🌐 Dashboard URL: http://localhost:8000"
echo " 📚 API Docs URL:  http://localhost:8000/docs"
echo "=============================================================="

exec "$PYTHON_BIN" app.py "$@"
