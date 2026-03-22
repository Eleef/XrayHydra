#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ -x ".venv/bin/python" ]]; then
    PYTHON=".venv/bin/python"
else
    if command -v python3 >/dev/null 2>&1; then
        BOOTSTRAP_PYTHON="python3"
    elif command -v python >/dev/null 2>&1; then
        BOOTSTRAP_PYTHON="python"
    else
        echo "[xray-prism] Python 3 not found. Please install Python 3.10+ first." >&2
        exit 1
    fi

    echo "[xray-prism] Creating virtual environment..."
    "$BOOTSTRAP_PYTHON" -m venv .venv
    PYTHON=".venv/bin/python"
fi

if ! "$PYTHON" -c "import fastapi,uvicorn,requests,yaml,dotenv" >/dev/null 2>&1; then
    echo "[xray-prism] Installing dependencies..."
    "$PYTHON" -m pip install --upgrade pip
    "$PYTHON" -m pip install -r requirements.txt
fi

echo "[xray-prism] Starting server..."
exec "$PYTHON" server.py "$@"

