"""
pipeline/generator.py
Phase 2: Parallel file generation with stateful self-healing repair loop
and persistent repair memory.
"""

import json
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
from utils.cleaner import strip_markdown
from utils.compiler import check_python_file
from pipeline.tester import run_test_pipeline

logger = logging.getLogger(__name__)


# ── Persistent repair memory ───────────────────────────────────────────────────

def _repair_history_path(path: str) -> Path:
    """Return the JSON file path that stores repair history for a source file."""
    safe = path.replace("/", "_").replace("\\", "_")
    config.REPAIR_DIR.mkdir(parents=True, exist_ok=True)
    return config.REPAIR_DIR / f"{safe}.json"


def load_repair_history(path: str) -> list[str]:
    """Load persisted repair history for a file (empty list if none)."""
    p = _repair_history_path(path)
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, list):
                logger.debug("Loaded %d repair history entries for %s", len(data), path)
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return []


def save_repair_history(path: str, history: list[str]):
    """Persist repair history for a file to disk."""
    p = _repair_history_path(path)
    p.write_text(json.dumps(history, indent=2), encoding="utf-8")


# ── Single-file generation ─────────────────────────────────────────────────────

def generate_file(
    file_info: dict,
    consensus_output: str,
    coder,
    fixer,
    import_validator,
    test_generator,
    use_cache: bool = True,
) -> dict:
    """
    Generate, validate, and (if needed) repair a single file.

    Returns a result dict:
        { "path": str, "success": bool, "attempts": int, "error": str|None }
    """
    path        = file_info["path"]
    description = file_info["description"]
    depends_on  = file_info.get("depends_on", [])
    context_structure = "\n".join([path] + depends_on)

    full_path: Path = config.PROJECT_DIR / path
    full_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Generating: %s", path)

    # ── Initial code generation ────────────────────────────────────────────────
    raw_code = coder.run(
        f"""PROJECT SPECIFICATION

{consensus_output}

PROJECT STRUCTURE

{context_structure}

CURRENT FILE

{path}

FILE DESCRIPTION

{description}

IMPORTANT:

Only generate code for:
{path}

The generated code must be compatible with
all files listed in PROJECT STRUCTURE.

Use imports that match the structure.

Do not generate code for any other file.

Do not use markdown.

Return only file content.
""",
        use_cache=use_cache,
    )

    validated_code = strip_markdown(raw_code)
    full_path.write_text(validated_code, encoding="utf-8")

    # ── Validate ───────────────────────────────────────────────────────────────
    is_valid, error, error_type = _validate(
        path, validated_code, context_structure, full_path,
        consensus_output, description, import_validator, test_generator, use_cache,
    )

    if is_valid:
        logger.info("✓ Passed: %s", path)
        return {"path": path, "success": True, "attempts": 0, "error": None}

    # ── Repair loop ────────────────────────────────────────────────────────────
    # Load any prior repair history from disk so we don't repeat known-bad fixes
    repair_history = load_repair_history(path)
    final_error = error

    for attempt in range(1, config.MAX_RETRIES + 1):
        logger.warning("Fix attempt %d/%d for: %s [%s]", attempt, config.MAX_RETRIES, path, error_type)

        formatted_history = "\n---\n".join(repair_history)

        fixed_code = fixer.run(
            f"""ERROR TYPE:
{error_type}

PROJECT STRUCTURE:
{context_structure}

CURRENT FILE:
{path}

FILE DESCRIPTION:
{description}

ERROR LOG:
{error}

REPAIR HISTORY:
{formatted_history}

CURRENT CODE:
{validated_code}
""",
            use_cache=False,  # Never cache fixer output — each attempt must be fresh
        )

        validated_code = strip_markdown(fixed_code)
        full_path.write_text(validated_code, encoding="utf-8")

        # Append this attempt to history and persist immediately
        repair_history.append(f"[{error_type}]\n{error}")
        save_repair_history(path, repair_history)

        # On PYTEST_FAILURE, force the test file to be regenerated so stale
        # broken tests don't keep blocking valid source code.
        force_regen = (error_type == "PYTEST_FAILURE")

        is_valid, error, error_type = _validate(
            path, validated_code, context_structure, full_path,
            consensus_output, description, import_validator, test_generator,
            use_cache, force_regenerate_tests=force_regen,
        )

        if is_valid:
            logger.info("✓ Fixed after %d attempt(s): %s", attempt, path)
            return {"path": path, "success": True, "attempts": attempt, "error": None}

        final_error = error
        # Save error log for inspection
        _save_error_log(path, error)

    logger.error("✗ Still failing after %d attempts: %s", config.MAX_RETRIES, path)
    return {"path": path, "success": False, "attempts": config.MAX_RETRIES, "error": final_error}


def _validate(path, validated_code, context_structure, full_path,
              consensus_output, description, import_validator, test_generator,
              use_cache, force_regenerate_tests=False):
    """Run compilation check then full test pipeline. Returns (is_valid, error, error_type)."""
    if not path.endswith(".py"):
        return True, None, None

    is_valid, error = check_python_file(str(full_path))
    if not is_valid:
        return False, error, "COMPILATION_ERROR"

    return run_test_pipeline(
        path, validated_code, context_structure, full_path,
        consensus_output, description, import_validator, test_generator,
        use_cache, force_regenerate_tests=force_regenerate_tests,
    )


def _save_error_log(path: str, error: str):
    """Write final error to the errors directory for post-run inspection."""
    config.ERRORS_DIR.mkdir(parents=True, exist_ok=True)
    safe = path.replace("/", "_").replace("\\", "_")
    error_file = config.ERRORS_DIR / f"{safe}.txt"
    error_file.write_text(error or "", encoding="utf-8")


# ── Parallel generation entry point ───────────────────────────────────────────

def generate_all_files(
    file_plan: list[dict],
    consensus_output: str,
    coder,
    fixer,
    import_validator,
    test_generator,
    use_cache: bool = True,
    max_workers: int = None,
) -> list[dict]:
    """
    Generate all files in the plan using a thread pool.

    Files with no `depends_on` can run in parallel; those with dependencies
    wait until their dependencies are done. This is a simple wave-based
    topological schedule.

    Returns a list of result dicts from generate_file().
    """
    workers = max_workers or config.MAX_WORKERS
    results = []

    # Build a simple dependency-aware schedule:
    # Wave 0 = files with no depends_on, Wave N = files whose deps are all done.
    completed_paths: set[str] = set()
    remaining = list(file_plan)

    logger.info("Starting parallel generation: %d files, %d workers", len(file_plan), workers)

    while remaining:
        # Files whose dependencies are all satisfied
        ready = [
            fi for fi in remaining
            if all(dep in completed_paths for dep in fi.get("depends_on", []))
        ]

        if not ready:
            # Circular dependency or unsatisfiable deps — fall back to sequential
            logger.warning("Dependency deadlock detected; processing remaining files sequentially.")
            ready = remaining

        remaining = [fi for fi in remaining if fi not in ready]

        with ThreadPoolExecutor(max_workers=min(workers, len(ready))) as executor:
            futures = {
                executor.submit(
                    generate_file,
                    fi, consensus_output,
                    coder, fixer, import_validator, test_generator,
                    use_cache,
                ): fi["path"]
                for fi in ready
            }
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                completed_paths.add(result["path"])
                status = "✓" if result["success"] else "✗"
                logger.info("%s %s", status, result["path"])

    return results
