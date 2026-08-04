#!/bin/bash
set -e
cd /home/ubuntu/agentforge

echo "=== Checking ollama health ==="
for i in $(seq 1 18); do
  STATUS=$(docker inspect --format='{{.State.Health.Status}}' ollama 2>/dev/null || echo "missing")
  echo "  attempt $i: $STATUS"
  if [ "$STATUS" = "healthy" ]; then
    echo "Ollama is healthy!"
    break
  fi
  sleep 10
done

echo ""
echo "=== Starting agentforge container ==="
export AGENTFORGE_TASK="Build a simple Python Hello World script."
export AGENTFORGE_PLANNER_MODEL="qwen2.5:3b"
export AGENTFORGE_CODER_MODEL="qwen2.5:3b"
export AGENTFORGE_WORKERS="1"

docker compose run --rm agentforge 2>&1 | tee /home/ubuntu/agentforge-run.log

echo ""
echo "=== Run complete. Output files: ==="
find /home/ubuntu/agentforge/output -type f 2>/dev/null | head -30 || echo "(no output yet)"
