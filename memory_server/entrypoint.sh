#!/bin/sh
set -e

MEMORY_PORT="${AGENTFORGE_MEMORY_SERVER_PORT:-8081}"
MEMORY_DATA_DIR="${AGENTFORGE_MEMORY_SERVER_DATA_DIR:-/app/memory_data}"
OLLAMA_HOST="${OLLAMA_HOST:-http://ollama:11434}"

echo "[memory-server] Data directory: $MEMORY_DATA_DIR"
mkdir -p "$MEMORY_DATA_DIR"

echo "[memory-server] Waiting for Ollama at $OLLAMA_HOST ..."
MAX_WAIT=60
WAITED=0

until python -c "
import urllib.request, sys
try:
    urllib.request.urlopen('$OLLAMA_HOST/api/tags', timeout=4)
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    if [ "$WAITED" -ge "$MAX_WAIT" ]; then
        echo "[memory-server] WARNING: Ollama not ready, starting anyway"
        break
    fi
    echo "[memory-server] Ollama not ready yet, retrying in 5s... (${WAITED}s elapsed)"
    sleep 5
    WAITED=$((WAITED + 5))
done

echo "[memory-server] Starting Memory Server on port $MEMORY_PORT..."
exec python -m uvicorn memory_server.main:app --host 0.0.0.0 --port "$MEMORY_PORT"