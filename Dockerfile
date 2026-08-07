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
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

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
RUN mkdir -p /app/output

# Entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Point agentforge at the ollama sidecar
    OLLAMA_HOST=http://ollama:11434 \
    # v1.0 defaults
    AGENTFORGE_AUTONOMOUS=false \
    AGENTFORGE_MAX_ITERATIONS=50 \
    AGENTFORGE_LANGUAGE= \
    AGENTFORGE_POLYGLOT=false \
    AGENTFORGE_INTEGRATION=false

ENTRYPOINT ["/entrypoint.sh"]
