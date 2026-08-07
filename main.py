"""
main.py — AgentForge CLI entry point.

Usage:
    python main.py "Build a FastAPI Todo API with JWT auth"
    python main.py "..." --planner-model qwen2.5:7b --coder-model qwen2.5-coder:14b
    python main.py "..." --no-cache
    python main.py "..." --clear-cache
    python main.py --list-models

v1.0 Features:
    python main.py --autonomous "Build and maintain a REST API" --max-iterations 100
    python main.py --memory-stats
    python main.py --memory-export memory_backup.json
    python main.py --language typescript "Build a React dashboard"
"""

import argparse
import asyncio
import json
import logging
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

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
from agents.autonomous_agent import AutonomousAgent
from agents.polyglot_file_planner import PolyglotFilePlanner

from utils.json_parser import parse_json
from utils.memory import get_memory_store, recall_relevant
from utils.language import detect_language
from config import SUPPORTED_LANGUAGES
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

    # ─── v1.0: Autonomous Mode ───────────────────────────────────────────────────
    auto_group = parser.add_argument_group("Autonomous Mode (v1.0)")
    auto_group.add_argument(
        "--autonomous",
        action="store_true",
        help="Run in autonomous mode: continuously work on goals until completion.",
    )
    auto_group.add_argument(
        "--max-iterations",
        type=int,
        default=config.AUTONOMOUS_MAX_ITERATIONS,
        metavar="N",
        help=f"Max autonomous loop iterations. Default: {config.AUTONOMOUS_MAX_ITERATIONS}.",
    )
    auto_group.add_argument(
        "--goal-timeout",
        type=int,
        default=config.AUTONOMOUS_GOAL_TIMEOUT,
        metavar="SECONDS",
        help=f"Goal timeout in seconds. Default: {config.AUTONOMOUS_GOAL_TIMEOUT}.",
    )
    auto_group.add_argument(
        "--initial-goal",
        type=str,
        default=None,
        metavar="GOAL",
        help="Initial goal for autonomous mode (if not using task argument).",
    )

    # ─── v1.0: Multi-Language Support ────────────────────────────────────────────
    lang_group = parser.add_argument_group("Multi-Language Support (v1.0)")
    lang_choices = list(SUPPORTED_LANGUAGES.keys())
    lang_group.add_argument(
        "--language",
        choices=lang_choices,
        default=None,
        metavar="LANG",
        help=f"Target programming language. Default: auto-detect. Choices: {', '.join(lang_choices)}",
    )
    lang_group.add_argument(
        "--list-languages",
        action="store_true",
        help="List supported programming languages and exit.",
    )
    lang_group.add_argument(
        "--polyglot",
        action="store_true",
        help="Use polyglot file planner for multi-language projects.",
    )

    # ─── v1.0: Long-Term Memory ──────────────────────────────────────────────────
    mem_group = parser.add_argument_group("Long-Term Memory (v1.0)")
    mem_group.add_argument(
        "--memory-stats",
        action="store_true",
        help="Show memory statistics for current project and exit.",
    )
    mem_group.add_argument(
        "--memory-export",
        type=str,
        default=None,
        metavar="FILE",
        help="Export project memory to JSON file and exit.",
    )
    mem_group.add_argument(
        "--memory-import",
        type=str,
        default=None,
        metavar="FILE",
        help="Import project memory from JSON file.",
    )
    mem_group.add_argument(
        "--memory-clear",
        action="store_true",
        help="Clear all project memory and exit.",
    )
    mem_group.add_argument(
        "--project-id",
        type=str,
        default=None,
        metavar="ID",
        help="Project ID for memory isolation (auto-generated if not provided).",
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
    polyglot_planner = PolyglotFilePlanner(model=pm)
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

    task = args.task or args.initial_goal

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
    if args.polyglot:
        logger.info("Using polyglot file planner for language: %s", args.language or "auto")
        file_plan_dict = polyglot_planner.plan(
            consensus_output,
            language=args.language,
            project_dir=str(config.PROJECT_DIR)
        )
        file_plan_raw = json.dumps(file_plan_dict)
        config.FILE_PLAN_FILE.write_text(file_plan_raw, encoding="utf-8")
        files = file_plan_dict.get("files", [])
    else:
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


def run_autonomous(args):
    """Run the autonomous agent."""
    logger = logging.getLogger("agentforge")

    # Override output dir if requested
    if args.output_dir:
        config.OUTPUT_DIR  = Path(args.output_dir)
        config.CACHE_DIR   = config.OUTPUT_DIR / "cache"
        config.ERRORS_DIR  = config.OUTPUT_DIR / "errors"
        config.PROJECT_DIR = config.OUTPUT_DIR / "project"
        config.REPAIR_DIR  = config.OUTPUT_DIR / "repair_history"
        config.SPEC_FILE       = config.OUTPUT_DIR / "specification.md"
        config.FILE_PLAN_FILE  = config.OUTPUT_DIR / "file_plan.json"

    # Ensure dirs exist
    for d in [config.OUTPUT_DIR, config.CACHE_DIR, config.PROJECT_DIR,
              config.ERRORS_DIR, config.REPAIR_DIR, config.MEMORY_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    # Determine project ID
    project_id = args.project_id or f"auto_{int(time.time())}"

    # Create agents
    pm = args.planner_model
    cm = args.coder_model

    logger.info("Planner model : %s", pm)
    logger.info("Coder model   : %s", cm)
    logger.info("Project ID    : %s", project_id)

    analyst          = AnalystAgent(model=pm)
    architect        = ArchitectAgent(model=pm)
    critic           = CriticAgent(model=pm)
    planner          = PlannerAgent(model=pm)
    consensus        = ConsensusAgent(model=pm)
    polyglot_planner = PolyglotFilePlanner(model=pm)
    coder            = CoderAgent(model=cm)
    fixer            = FixerAgent(model=cm)
    import_validator = ImportValidatorAgent(model=cm)
    test_generator   = TestGeneratorAgent(model=cm)

    # Create autonomous agent
    auto_agent = AutonomousAgent(
        project_dir=config.PROJECT_DIR,
        project_id=project_id,
        max_iterations=args.max_iterations,
        goal_timeout=args.goal_timeout,
    )

    # Register agents
    auto_agent.register_agent("analyst", analyst)
    auto_agent.register_agent("architect", architect)
    auto_agent.register_agent("critic", critic)
    auto_agent.register_agent("planner", planner)
    auto_agent.register_agent("consensus", consensus)
    auto_agent.register_agent("file_planner", polyglot_planner)
    auto_agent.register_agent("coder", coder)
    auto_agent.register_agent("fixer", fixer)
    auto_agent.register_agent("import_validator", import_validator)
    auto_agent.register_agent("test_generator", test_generator)

    # Add initial goal
    initial_goal = args.task or args.initial_goal
    if initial_goal:
        auto_agent.add_goal(initial_goal, priority=10, tags=["initial", "user"])
    else:
        logger.error("No initial goal provided for autonomous mode")
        sys.exit(1)

    # Set up callbacks
    def on_goal_complete(goal):
        logger.info("✓ Goal completed: %s", goal.description[:80])

    def on_task_complete(task):
        logger.info("  ✓ Task completed: %s", task.description[:60])

    def on_error(task, error):
        logger.warning("  ✗ Task failed: %s - %s", task.description[:60], error)

    auto_agent.on_goal_complete = on_goal_complete
    auto_agent.on_task_complete = on_task_complete
    auto_agent.on_error = on_error

    # Run autonomous loop
    logger.info("Starting autonomous agent...")
    summary = auto_agent.run()

    # Print summary
    logger.info("\n=== Autonomous Agent Summary ===")
    logger.info("Project ID       : %s", summary["project_id"])
    logger.info("Iterations       : %d", summary["iterations"])
    logger.info("Goals Total      : %d", summary["goals_total"])
    logger.info("Goals Completed  : %d", summary["goals_completed"])
    logger.info("Goals Failed     : %d", summary["goals_failed"])
    logger.info("Tasks Total      : %d", summary["tasks_total"])
    logger.info("Tasks Completed  : %d", summary["tasks_completed"])
    logger.info("Tasks Failed     : %d", summary["tasks_failed"])

    return summary


def handle_memory_commands(args):
    """Handle memory-related CLI commands."""
    logger = logging.getLogger("agentforge")

    project_id = args.project_id or "default"
    store = get_memory_store(project_id)

    if args.memory_stats:
        stats = store.stats()
        print(f"\n=== Memory Statistics (Project: {project_id}) ===")
        print(f"Total Entries    : {stats['total_entries']}")
        print(f"Categories       : {stats['categories']}")
        if stats['oldest']:
            print(f"Oldest Entry     : {datetime.fromtimestamp(stats['oldest'])}")
        if stats['newest']:
            print(f"Newest Entry     : {datetime.fromtimestamp(stats['newest'])}")
        return

    if args.memory_export:
        export_path = Path(args.memory_export)
        store.export(export_path)
        print(f"Memory exported to {export_path}")
        return

    if args.memory_import:
        import_path = Path(args.memory_import)
        if not import_path.exists():
            logger.error("Import file not found: %s", import_path)
            sys.exit(1)
        store.import_memory(import_path)
        print(f"Memory imported from {import_path}")
        return

    if args.memory_clear:
        confirm = input(f"Clear all memory for project '{project_id}'? [y/N]: ")
        if confirm.lower() == 'y':
            store.entries.clear()
            store._save()
            print("Memory cleared")
        else:
            print("Cancelled")
        return


def handle_list_languages():
    """List supported languages."""
    print("Supported Programming Languages:")
    for lang, cfg in SUPPORTED_LANGUAGES.items():
        ext = ", ".join(cfg["extensions"])
        print(f"  {lang:15} extensions: {ext}")
        print(f"  {'':15} test: {cfg['test_pattern']}, framework: {cfg['test_framework']}")
        print(f"  {'':15} package: {cfg['package_manager']}, config: {', '.join(cfg['config_files'])}")
        print()


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = build_parser()
    args   = parser.parse_args()

    _setup_logging(args.log_level)
    logger = logging.getLogger("agentforge")

    # Handle standalone commands that don't need a task
    if args.list_models:
        print("Available models:")
        for m in AVAILABLE_MODELS:
            print(f"  {m}")
        sys.exit(0)

    if args.list_languages:
        handle_list_languages()
        sys.exit(0)

    if args.memory_stats or args.memory_export or args.memory_import or args.memory_clear:
        handle_memory_commands(args)
        sys.exit(0)

    # Autonomous mode
    if args.autonomous:
        if not args.task and not args.initial_goal:
            parser.error("Autonomous mode requires a task or --initial-goal")
        try:
            run_autonomous(args)
        except KeyboardInterrupt:
            logger.info("Interrupted by user.")
            sys.exit(0)
        except Exception as exc:
            logger.exception("Autonomous agent failed: %s", exc)
            sys.exit(1)
        sys.exit(0)

    # Standard pipeline mode
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
    import time
    from datetime import datetime
    import json
    main()
