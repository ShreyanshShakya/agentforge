#!/bin/sh
set -e

OLLAMA_HOST="${OLLAMA_HOST:-http://ollama:11434}"
PLANNER_MODEL="${AGENTFORGE_PLANNER_MODEL:-qwen2.5:3b}"
CODER_MODEL="${AGENTFORGE_CODER_MODEL:-qwen2.5-coder:7b}"
TASK="${AGENTFORGE_TASK:-Build a simple FastAPI Hello World API.}"
WORKERS="${AGENTFORGE_WORKERS:-2}"

# ── 1. Wait for Ollama to be ready (Python, no curl needed) ───────────────────
echo "[entrypoint] Waiting for Ollama at $OLLAMA_HOST ..."
MAX_WAIT=120
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
        echo "[entrypoint] ERROR: Ollama did not become ready within ${MAX_WAIT}s"
        exit 1
    fi
    echo "[entrypoint] Ollama not ready yet, retrying in 5s... (${WAITED}s elapsed)"
    sleep 5
    WAITED=$((WAITED + 5))
done
echo "[entrypoint] Ollama is ready."

# ── 2. Pull required models (idempotent via Ollama REST API) ──────────────────
pull_model() {
    MODEL="$1"
    echo "[entrypoint] Pulling model: $MODEL (this may take several minutes on first run)"
    python -c "
import urllib.request, json, sys

url = '$OLLAMA_HOST/api/pull'
payload = json.dumps({'name': '$MODEL', 'stream': False}).encode()
req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read())
        status = data.get('status', '')
        print(f'  Pull response: {status}')
        sys.exit(0)
except Exception as e:
    print(f'  WARNING: pull request failed: {e}', file=sys.stderr)
    sys.exit(0)  # continue anyway — model may already be cached
"
    echo "[entrypoint] Model ready: $MODEL"
}

pull_model "$PLANNER_MODEL"
if [ "$CODER_MODEL" != "$PLANNER_MODEL" ]; then
    pull_model "$CODER_MODEL"
fi

# ── 3. Run AgentForge pipeline ────────────────────────────────────────────────
echo "[entrypoint] Starting AgentForge pipeline..."
echo "[entrypoint]   Task           : $TASK"
echo "[entrypoint]   Planner model  : $PLANNER_MODEL"
echo "[entrypoint]   Coder model    : $CODER_MODEL"
echo "[entrypoint]   Workers        : $WORKERS"

exec python main.py "$TASK" \
    --planner-model "$PLANNER_MODEL" \
    --coder-model   "$CODER_MODEL" \
    --workers       "$WORKERS" \
    --log-level     INFO
