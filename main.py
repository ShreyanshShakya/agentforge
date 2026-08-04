"""
main.py — AgentForge CLI entry point.

Usage:
    python main.py "Build a FastAPI Todo API with JWT auth"
    python main.py "..." --planner-model qwen2.5:7b --coder-model qwen2.5-coder:14b
    python main.py "..." --no-cache
    python main.py "..." --clear-cache
    python main.py --list-models
"""

import argparse
import logging
import shutil
import sys

import config
from config import AVAILABLE_MODELS

from agents.analyst       import AnalystAgent
from agents.architect     import ArchitectAgent
from agents.critic        import CriticAgent
from agents.planner       import PlannerAgent
from agents.consensus     import ConsensusAgent
from agents.file_planner  import FilePlannerAgent
from agents.coder         import CoderAgent
from agents.fixer         import FixerAgent
from agents.import_validator import ImportValidatorAgent
from agents.test_generator   import TestGeneratorAgent

from utils.json_parser import parse_json
from pipeline.generator import generate_all_files
from pipeline.integration import run_integration_phase, format_integration_report
from agents.dependency_agent import resolve_dependencies


# ── Logging setup ──────────────────────────────────────────────────────────────

def _setup_logging(level: str):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=config.LOG_FORMAT,
        datefmt=config.LOG_DATE,
    )


# ── CLI ────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentforge",
        description="AgentForge — autonomous multi-agent code generation pipeline",
    )

    parser.add_argument(
        "task",
        nargs="?",
        default=None,
        help="Natural language description of the project to build.",
    )

    # Model selection
    model_choices = AVAILABLE_MODELS
    parser.add_argument(
        "--planner-model",
        default=config.DEFAULT_PLANNER_MODEL,
        metavar="MODEL",
        help=(
            f"Ollama model for design-phase agents (analyst, architect, critic, planner, consensus, file-planner). "
            f"Default: {config.DEFAULT_PLANNER_MODEL}"
        ),
    )
    parser.add_argument(
        "--coder-model",
        default=config.DEFAULT_CODER_MODEL,
        metavar="MODEL",
        help=(
            f"Ollama model for code-generation agents (coder, fixer, import-validator, test-generator). "
            f"Default: {config.DEFAULT_CODER_MODEL}"
        ),
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Print available model options and exit.",
    )

    # Cache control
    cache_group = parser.add_mutually_exclusive_group()
    cache_group.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable cache reads; always call the LLM (results still saved).",
    )
    cache_group.add_argument(
        "--clear-cache",
        action="store_true",
        help="Delete all cached agent outputs before running.",
    )

    # Output
    parser.add_argument(
        "--output-dir",
        default=None,
        metavar="PATH",
        help="Override the output directory (default: ./output).",
    )

    # Parallelism
    parser.add_argument(
        "--workers",
        type=int,
        default=config.MAX_WORKERS,
        metavar="N",
        help=f"Number of parallel file-generation workers. Default: {config.MAX_WORKERS}.",
    )

    # Integration testing (v0.7)
    parser.add_argument(
        "--integration",
        action="store_true",
        help=(
            "Run post-generation integration phase: install dependencies, "
            "execute runtime test, and validate API endpoints (FastAPI/Flask)."
        ),
    )

    # Verbosity
    parser.add_argument(
        "--log-level",
        default=config.LOG_LEVEL,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help=f"Logging verbosity. Default: {config.LOG_LEVEL}.",
    )

    return parser


# ── Pipeline ───────────────────────────────────────────────────────────────────

def run_pipeline(args):
    logger = logging.getLogger("agentforge")

    # Override output dir if requested
    if args.output_dir:
        from pathlib import Path
        config.OUTPUT_DIR  = Path(args.output_dir)
        config.CACHE_DIR   = config.OUTPUT_DIR / "cache"
        config.ERRORS_DIR  = config.OUTPUT_DIR / "errors"
        config.PROJECT_DIR = config.OUTPUT_DIR / "project"
        config.REPAIR_DIR  = config.OUTPUT_DIR / "repair_history"
        config.SPEC_FILE       = config.OUTPUT_DIR / "specification.md"
        config.FILE_PLAN_FILE  = config.OUTPUT_DIR / "file_plan.json"

    use_cache = not args.no_cache

    # ── Create agents with chosen models ──────────────────────────────────────
    pm = args.planner_model
    cm = args.coder_model

    logger.info("Planner model : %s", pm)
    logger.info("Coder model   : %s", cm)

    analyst          = AnalystAgent(model=pm)
    architect        = ArchitectAgent(model=pm)
    critic           = CriticAgent(model=pm)
    planner          = PlannerAgent(model=pm)
    consensus        = ConsensusAgent(model=pm)
    file_planner     = FilePlannerAgent(model=pm)
    coder            = CoderAgent(model=cm)
    fixer            = FixerAgent(model=cm)
    import_validator = ImportValidatorAgent(model=cm)
    test_generator   = TestGeneratorAgent(model=cm)

    all_agents = [
        analyst, architect, critic, planner, consensus, file_planner,
        coder, fixer, import_validator, test_generator,
    ]

    # ── Clear cache if requested ───────────────────────────────────────────────
    if args.clear_cache:
        if config.CACHE_DIR.exists():
            shutil.rmtree(config.CACHE_DIR)
            logger.info("Cache cleared: %s", config.CACHE_DIR)

    # ── Ensure output dirs exist ───────────────────────────────────────────────
    for d in [config.OUTPUT_DIR, config.CACHE_DIR, config.PROJECT_DIR,
              config.ERRORS_DIR, config.REPAIR_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    task = args.task

    # ──────────────────────────────────────────────────────────────────────────
    # PHASE 1: System Design
    # ──────────────────────────────────────────────────────────────────────────
    logger.info("=== Phase 1: System Design ===")

    analysis = analyst.run(task, use_cache=use_cache)
    logger.info("\n--- ANALYST ---\n%s", analysis)

    architecture = architect.run(
        f"Requirements:\n{analysis}",
        use_cache=use_cache,
    )
    logger.info("\n--- ARCHITECT ---\n%s", architecture)

    critique = critic.run(
        f"Requirements:\n{analysis}\n\nArchitecture:\n{architecture}",
        use_cache=use_cache,
    )
    logger.info("\n--- CRITIC ---\n%s", critique)

    plan = planner.run(
        f"Requirements:\n{analysis}\n\nArchitecture:\n{architecture}\n\nCritique:\n{critique}",
        use_cache=use_cache,
    )
    logger.info("\n--- PLANNER ---\n%s", plan)

    consensus_output = consensus.run(
        f"ANALYSIS:\n{analysis}\n\nARCHITECTURE:\n{architecture}\n\n"
        f"CRITIQUE:\n{critique}\n\nPLAN:\n{plan}",
        use_cache=use_cache,
    )
    logger.info("\n--- CONSENSUS ---\n%s", consensus_output)

    config.SPEC_FILE.write_text(consensus_output, encoding="utf-8")
    logger.info("Specification saved: %s", config.SPEC_FILE)

    # ── File plan ──────────────────────────────────────────────────────────────
    file_plan_raw = file_planner.run(consensus_output, use_cache=use_cache)
    config.FILE_PLAN_FILE.write_text(file_plan_raw, encoding="utf-8")

    try:
        parsed = parse_json(file_plan_raw)
    except ValueError as exc:
        logger.error("Failed to parse file plan JSON: %s", exc)
        sys.exit(1)

    files = parsed.get("files")
    if not files or not isinstance(files, list):
        logger.error("file_plan.json is missing a 'files' array.")
        sys.exit(1)

    logger.info("File plan: %d files to generate", len(files))

    # ──────────────────────────────────────────────────────────────────────────
    # PHASE 2: Parallel Generation & Self-Healing
    # ──────────────────────────────────────────────────────────────────────────
    logger.info("=== Phase 2: Code Generation ===")

    results = generate_all_files(
        file_plan=files,
        consensus_output=consensus_output,
        coder=coder,
        fixer=fixer,
        import_validator=import_validator,
        test_generator=test_generator,
        use_cache=use_cache,
        max_workers=args.workers,
    )

    # ── Summary ────────────────────────────────────────────────────────────────
    passed  = [r for r in results if r["success"]]
    failed  = [r for r in results if not r["success"]]

    logger.info("\n=== Generation Summary ===")
    logger.info("Passed : %d", len(passed))
    logger.info("Failed : %d", len(failed))
    if failed:
        for r in failed:
            logger.warning("  ✗ %s (after %d attempts)", r["path"], r["attempts"])
    logger.info("Output : %s", config.PROJECT_DIR)

    # ──────────────────────────────────────────────────────────────────────────
    # PHASE 3: Integration Testing (opt-in via --integration)
    # ──────────────────────────────────────────────────────────────────────────
    if args.integration:
        logger.info("=== Phase 3: Integration Testing ===")

        # Step 1 — Dependency resolution
        logger.info("Installing project dependencies...")
        dep_ok, dep_err = resolve_dependencies(config.PROJECT_DIR)
        if not dep_ok:
            logger.warning("Dependency installation failed:\n%s", dep_err)
            logger.warning("Continuing with integration tests using system Python.")

        # Step 2 — Runtime + API validation
        integration_results = run_integration_phase(
            file_plan=files,
            project_dir=config.PROJECT_DIR,
        )
        logger.info(format_integration_report(integration_results))

        # Surface failures clearly
        rt = integration_results.get("runtime") or {}
        api = integration_results.get("api") or {}
        if not rt.get("success", True):
            logger.warning("Runtime integration test FAILED.")
        if api and not api.get("success", True):
            logger.warning("API endpoint validation FAILED.")


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = build_parser()
    args   = parser.parse_args()

    _setup_logging(args.log_level)
    logger = logging.getLogger("agentforge")

    if args.list_models:
        print("Available models:")
        for m in AVAILABLE_MODELS:
            print(f"  {m}")
        sys.exit(0)

    if not args.task:
        parser.error("A task description is required. Example:\n  python main.py \"Build a FastAPI Todo API\"")

    try:
        run_pipeline(args)
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
        sys.exit(0)
    except Exception as exc:
        logger.exception("Pipeline failed with an unexpected error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
