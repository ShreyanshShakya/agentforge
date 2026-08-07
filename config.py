"""
AgentForge Configuration
All tuneable settings live here. Override via CLI args or environment variables.
"""

from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────

ROOT_DIR    = Path(__file__).parent.resolve()
OUTPUT_DIR  = ROOT_DIR / "output"
CACHE_DIR   = OUTPUT_DIR / "cache"
ERRORS_DIR  = OUTPUT_DIR / "errors"
PROJECT_DIR = OUTPUT_DIR / "project"
REPAIR_DIR  = OUTPUT_DIR / "repair_history"

SPEC_FILE       = OUTPUT_DIR / "specification.md"
FILE_PLAN_FILE  = OUTPUT_DIR / "file_plan.json"

# ─── Available Models ─────────────────────────────────────────────────────────
# Users can select any model from this list via --planner-model / --coder-model
# or add their own Ollama model names.

AVAILABLE_MODELS = [
    "qwen2.5:3b",
    "qwen2.5:7b",
    "qwen2.5:14b",
    "qwen2.5-coder:7b",
    "qwen2.5-coder:14b",
    "llama3.2:3b",
    "llama3.1:8b",
    "mistral:7b",
    "deepseek-coder:6.7b",
    "codellama:7b",
    "gemma2:9b",
]

# ─── Default Model Assignments ────────────────────────────────────────────────
# "planner" models are used for design-phase agents (analyst, architect, etc.)
# "coder"   models are used for code-generation agents (coder, fixer, etc.)

DEFAULT_PLANNER_MODEL = "qwen2.5:3b"
DEFAULT_CODER_MODEL   = "qwen2.5-coder:7b"

# ─── Agent num_predict Defaults ───────────────────────────────────────────────

NUM_PREDICT = {
    "analyst":          500,
    "architect":        700,
    "critic":           500,
    "planner":         1200,
    "consensus":        500,
    "file_planner":    2000,
    "coder":           4000,
    "fixer":           3000,
    "import_validator":1000,
    "test_generator":  3000,
    "validator":       3000,
}

# ─── Pipeline Settings ────────────────────────────────────────────────────────

MAX_RETRIES        = 3      # Max fixer retry attempts per file
SUBPROCESS_TIMEOUT = 60     # Seconds before a test subprocess is killed
MAX_WORKERS        = 4      # ThreadPoolExecutor workers for parallel generation

# ─── Logging ──────────────────────────────────────────────────────────────────

LOG_LEVEL  = "INFO"   # DEBUG | INFO | WARNING | ERROR
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE   = "%H:%M:%S"

# ─── v1.0: Autonomous Agent Settings ──────────────────────────────────────────

AUTONOMOUS_MAX_ITERATIONS   = 50      # Max autonomous loop iterations
AUTONOMOUS_GOAL_TIMEOUT     = 300     # Seconds before goal times out
AUTONOMOUS_IDLE_THRESHOLD   = 3       # Idle cycles before proposing new tasks

# ─── v1.0: Multi-Language Support ─────────────────────────────────────────────

SUPPORTED_LANGUAGES = {
    "python": {
        "extensions": [".py"],
        "test_pattern": "test_*.py",
        "test_framework": "pytest",
        "build_cmd": None,
        "run_cmd": "python",
        "package_manager": "pip",
        "config_files": ["requirements.txt", "pyproject.toml", "setup.py"],
        "validator": "python",
    },
    "javascript": {
        "extensions": [".js", ".jsx", ".mjs"],
        "test_pattern": "*.test.js",
        "test_framework": "jest",
        "build_cmd": None,
        "run_cmd": "node",
        "package_manager": "npm",
        "config_files": ["package.json"],
        "validator": "node",
    },
    "typescript": {
        "extensions": [".ts", ".tsx"],
        "test_pattern": "*.test.ts",
        "test_framework": "jest",
        "build_cmd": "tsc",
        "run_cmd": "node",
        "package_manager": "npm",
        "config_files": ["package.json", "tsconfig.json"],
        "validator": "tsc",
    },
    "go": {
        "extensions": [".go"],
        "test_pattern": "*_test.go",
        "test_framework": "go test",
        "build_cmd": "go build",
        "run_cmd": "go run",
        "package_manager": "go mod",
        "config_files": ["go.mod", "go.sum"],
        "validator": "go vet",
    },
    "rust": {
        "extensions": [".rs"],
        "test_pattern": "*_test.rs",
        "test_framework": "cargo test",
        "build_cmd": "cargo build",
        "run_cmd": "cargo run",
        "package_manager": "cargo",
        "config_files": ["Cargo.toml"],
        "validator": "cargo check",
    },
    "java": {
        "extensions": [".java"],
        "test_pattern": "*Test.java",
        "test_framework": "junit",
        "build_cmd": "mvn compile",
        "run_cmd": "java",
        "package_manager": "maven",
        "config_files": ["pom.xml", "build.gradle"],
        "validator": "javac",
    },
    "csharp": {
        "extensions": [".cs"],
        "test_pattern": "*Tests.cs",
        "test_framework": "dotnet test",
        "build_cmd": "dotnet build",
        "run_cmd": "dotnet run",
        "package_manager": "nuget",
        "config_files": ["*.csproj", "*.sln"],
        "validator": "dotnet build",
    },
}

DEFAULT_LANGUAGE = "python"
LANGUAGE_DETECTION_ENABLED = True

# ─── v1.0: Long-Term Project Memory ───────────────────────────────────────────

MEMORY_DIR           = OUTPUT_DIR / "memory"
MEMORY_VECTOR_STORE  = MEMORY_DIR / "vectors"
MEMORY_EMBEDDINGS_MODEL = "nomic-embed-text"  # Ollama embedding model
MEMORY_MAX_ENTRIES   = 10000
MEMORY_SIMILARITY_THRESHOLD = 0.75
MEMORY_TTL_DAYS      = 90
MEMORY_AUTO_SAVE     = True

# ─── Paths (extended) ──────────────────────────────────────────────────────────

MEMORY_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_VECTOR_STORE.mkdir(parents=True, exist_ok=True)
