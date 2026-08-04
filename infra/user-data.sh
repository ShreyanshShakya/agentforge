#!/bin/bash
set -eux

# ── System update & Docker install ───────────────────────────────────────────
apt-get update -y
apt-get install -y ca-certificates curl gnupg lsb-release rsync

# Docker official GPG key + repo
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

systemctl enable --now docker
usermod -aG docker ubuntu

# Create project directory ready for rsync
mkdir -p /home/ubuntu/agentforge/output
chown -R ubuntu:ubuntu /home/ubuntu/agentforge

echo "Bootstrap complete. Docker $(docker --version)" >> /var/log/agentforge-bootstrap.log
