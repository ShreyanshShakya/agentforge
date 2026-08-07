#!/bin/sh
set -e

WEBUI_PORT="${AGENTFORGE_WEBUI_PORT:-8080}"
OLLAMA_HOST="${OLLAMA_HOST:-http://ollama:11434}"

echo "[webui] Waiting for Ollama at $OLLAMA_HOST ..."
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
        echo "[webui] WARNING: Ollama not ready, starting anyway"
        break
    fi
    echo "[webui] Ollama not ready yet, retrying in 5s... (${WAITED}s elapsed)"
    sleep 5
    WAITED=$((WAITED + 5))
done

echo "[webui] Starting Web UI on port $WEBUI_PORT..."
exec python -m uvicorn webui.main:app --host 0.0.0.0 --port "$WEBUI_PORT"