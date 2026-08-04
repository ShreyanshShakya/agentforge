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
