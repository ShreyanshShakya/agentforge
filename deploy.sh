#!/usr/bin/env bash
# deploy.sh — sync local AgentForge changes to EC2 and re-run
# Usage: bash deploy.sh [task]
set -euo pipefail

REGION="ap-south-1"
INSTANCE_ID="i-02016f7f815c2fffe"
KEY_FILE="$(dirname "$0")/agentforge-key.pem"
REMOTE_DIR="/home/ubuntu/agentforge"
TASK="${1:-Build a simple Python Hello World script.}"

# ── Get instance public IP ────────────────────────────────────────────────────
echo "[deploy] Fetching instance public IP..."
PUBLIC_IP=$(aws ec2 describe-instances \
  --region "$REGION" \
  --instance-ids "$INSTANCE_ID" \
  --query "Reservations[0].Instances[0].PublicIpAddress" \
  --output text)

if [ -z "$PUBLIC_IP" ] || [ "$PUBLIC_IP" = "None" ]; then
  echo "[deploy] ERROR: Could not get public IP. Is the instance running?"
  exit 1
fi

echo "[deploy] Instance IP: $PUBLIC_IP"

SSH_OPTS="-i $KEY_FILE -o StrictHostKeyChecking=no -o ConnectTimeout=10"

# ── Wait for SSH ───────────────────────────────────────────────────────────────
echo "[deploy] Waiting for SSH..."
for i in $(seq 1 30); do
  if ssh $SSH_OPTS ubuntu@"$PUBLIC_IP" "echo ok" > /dev/null 2>&1; then
    echo "[deploy] SSH ready."
    break
  fi
  echo "  attempt $i..."
  sleep 10
done

# ── Rsync source (exclude output/, .git, example/) ────────────────────────────
echo "[deploy] Syncing code..."
rsync -av --exclude='.git' --exclude='output/' --exclude='example/' \
  -e "ssh $SSH_OPTS" \
  "$(dirname "$0")/" \
  ubuntu@"$PUBLIC_IP":"$REMOTE_DIR/"

# ── Re-run pipeline with new task ─────────────────────────────────────────────
echo "[deploy] Starting pipeline on EC2..."
ssh $SSH_OPTS ubuntu@"$PUBLIC_IP" bash -s << EOF
  cd $REMOTE_DIR
  export AGENTFORGE_TASK="$TASK"
  export AGENTFORGE_PLANNER_MODEL="qwen2.5:3b"
  export AGENTFORGE_CODER_MODEL="qwen2.5:3b"
  export AGENTFORGE_WORKERS="1"
  docker compose up --build agentforge 2>&1 | tee ~/agentforge-run.log
  echo "--- Pipeline output ---"
  ls -la output/project/ 2>/dev/null || echo "(no output/project yet)"
EOF

echo "[deploy] Done. SSH in with:"
echo "  ssh -i $KEY_FILE ubuntu@$PUBLIC_IP"
