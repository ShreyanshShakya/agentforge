# ── Stage 1: builder (install deps) ──────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /app

# Install build tools + multi-language runtimes
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        curl \
        git \
        # Node.js for JavaScript/TypeScript
        nodejs \
        npm \
        # Go
        golang-go \
        # Rust
        cargo \
        rustc \
        # Java
        openjdk-21-jdk-headless \
        maven \
        # .NET
        dotnet-sdk-8.0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY webui/requirements.txt ./webui-requirements.txt
COPY memory_server/requirements.txt ./memory-server-requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt \
    && pip install --no-cache-dir --prefix=/install -r webui-requirements.txt \
    && pip install --no-cache-dir --prefix=/install -r memory-server-requirements.txt

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.13-slim

WORKDIR /app

# Install runtime dependencies for multi-language support
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        git \
        nodejs \
        npm \
        golang-go \
        cargo \
        rustc \
        openjdk-21-jdk-headless \
        maven \
        dotnet-runtime-8.0 \
        # For Ollama embedding model
        libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Create output directory
RUN mkdir -p /app/output /app/memory_data

# Entrypoint scripts
COPY entrypoint.sh /entrypoint.sh
COPY webui/entrypoint.sh /webui-entrypoint.sh
COPY memory_server/entrypoint.sh /memory-server-entrypoint.sh
RUN chmod +x /entrypoint.sh /webui-entrypoint.sh /memory-server-entrypoint.sh

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Point agentforge at the ollama sidecar
    OLLAMA_HOST=http://ollama:11434 \
    # v1.0 defaults
    AGENTFORGE_AUTONOMOUS=false \
    AGENTFORGE_MAX_ITERATIONS=50 \
    AGENTFORGE_LANGUAGE= \
    AGENTFORGE_POLYGLOT=false \
    AGENTFORGE_INTEGRATION=false \
    # v1.1 defaults
    AGENTFORGE_WEBUI_PORT=8080 \
    AGENTFORGE_MEMORY_SERVER_PORT=8081 \
    AGENTFORGE_MEMORY_SERVER_DATA_DIR=/app/memory_data

ENTRYPOINT ["/entrypoint.sh"]
