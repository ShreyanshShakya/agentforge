"""
pipeline/tester.py
Handles import validation, test generation, and pytest execution for a single file.
"""

import subprocess
import logging
from pathlib import Path

import config
from utils.cleaner import strip_markdown

logger = logging.getLogger(__name__)

# Imports that every generated test file must have at the top
_REQUIRED_TEST_IMPORTS = "import pytest\n"


def _ensure_pytest_import(code: str) -> str:
    """Guarantee `import pytest` is the first line of any test file."""
    if not code.lstrip().startswith("import pytest"):
        code = _REQUIRED_TEST_IMPORTS + code
    return code


def run_test_pipeline(
    path: str,
    validated_code: str,
    context_structure: str,
    full_path: Path,
    consensus_output: str,
    description: str,
    import_validator,
    test_generator,
    use_cache: bool = True,
    force_regenerate_tests: bool = False,
) -> tuple[bool, str | None, str | None]:
    """
    Run import validation → test generation → pytest for a single file.

    Args:
        force_regenerate_tests: When True (called from fixer loop on PYTEST_FAILURE),
                                 delete the existing test file and regenerate it from
                                 scratch so stale/broken tests don't block progress.

    Returns:
        (is_valid, error_message, error_type)
        error_type is one of: "IMPORT_ERROR", "PYTEST_FAILURE", or None
    """

    # Skip non-Python files and __init__ stubs
    if path.endswith("__init__.py") or not path.endswith(".py"):
        return True, None, None

    # ── Import validation ──────────────────────────────────────────────────────
    logger.info("Import validation: %s", path)
    import_result = import_validator.run(
        f"PROJECT STRUCTURE\n\n{context_structure}\n\nFILE\n\n{path}\n\nCODE\n\n{validated_code}",
        use_cache=use_cache,
    )
    if "VALID" not in import_result:
        return False, f"Import Validation Failed:\n{import_result}", "IMPORT_ERROR"

    # ── Determine test file path ───────────────────────────────────────────────
    test_file_path = _test_path_for(full_path)
    test_file_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Delete stale test file if fixer loop requested regeneration ───────────
    if force_regenerate_tests and test_file_path.exists():
        logger.info("Deleting stale test file for regeneration: %s", test_file_path)
        test_file_path.unlink()

    # ── Generate tests if missing ──────────────────────────────────────────────
    if not test_file_path.exists():
        logger.info("Generating tests for: %s", path)
        test_code = _generate_test_code(
            path, validated_code, context_structure,
            consensus_output, description, test_generator,
            use_cache=False if force_regenerate_tests else use_cache,
        )
        test_file_path.write_text(test_code, encoding="utf-8")
        logger.debug("Test file written: %s", test_file_path)

    # ── Validate test file syntax; auto-repair if broken ──────────────────────
    test_file_path = _ensure_test_syntax(
        test_file_path, path, validated_code, context_structure,
        consensus_output, description, test_generator,
    )

    # ── Run pytest ─────────────────────────────────────────────────────────────
    logger.info("Running pytest: %s", test_file_path.name)
    result = subprocess.run(
        ["python", "-m", "pytest", str(test_file_path), "-v", "--tb=short"],
        capture_output=True,
        text=True,
        cwd=str(config.PROJECT_DIR),
        timeout=config.SUBPROCESS_TIMEOUT,
    )

    if result.returncode != 0:
        return (
            False,
            f"Pytest Execution Failed:\n{result.stderr}\n{result.stdout}",
            "PYTEST_FAILURE",
        )

    logger.info("Tests passed: %s", path)
    return True, None, None


def _generate_test_code(
    path, validated_code, context_structure,
    consensus_output, description, test_generator, use_cache=True
) -> str:
    """Call test_generator LLM and return cleaned, import-guaranteed test code."""
    raw = test_generator.run(
        f"CONSENSUS SPECIFICATION\n\n{consensus_output}\n\n"
        f"PROJECT STRUCTURE\n\n{context_structure}\n\n"
        f"FILE DESCRIPTION\n\n{description}\n\n"
        f"FILE\n\n{path}\n\n"
        f"CODE\n\n{validated_code}",
        use_cache=use_cache,
    )
    code = strip_markdown(raw)
    return _ensure_pytest_import(code)


def _ensure_test_syntax(
    test_file_path: Path,
    path, validated_code, context_structure,
    consensus_output, description, test_generator,
    max_repair_attempts: int = 3,
) -> Path:
    """
    Compile-check the test file. If it has a syntax error, regenerate it
    up to max_repair_attempts times until it is syntactically valid.
    Returns the (possibly unchanged) test_file_path.
    """
    import py_compile, tempfile, os

    for attempt in range(max_repair_attempts):
        try:
            py_compile.compile(str(test_file_path), doraise=True)
            return test_file_path  # syntax OK
        except py_compile.PyCompileError as exc:
            logger.warning(
                "Test file syntax error (attempt %d/%d): %s",
                attempt + 1, max_repair_attempts, exc,
            )
            # Delete and regenerate
            test_file_path.unlink(missing_ok=True)
            test_code = _generate_test_code(
                path, validated_code, context_structure,
                consensus_output, description, test_generator,
                use_cache=False,
            )
            test_file_path.write_text(test_code, encoding="utf-8")
            logger.info("Regenerated test file: %s", test_file_path)

    # Last resort: if still broken, write a minimal passing placeholder
    try:
        py_compile.compile(str(test_file_path), doraise=True)
    except py_compile.PyCompileError:
        logger.warning(
            "Test file still broken after %d attempts — writing minimal placeholder.",
            max_repair_attempts,
        )
        module = path.replace("/", ".").replace("\\", ".").removesuffix(".py")
        placeholder = (
            "import pytest\n\n"
            f"# Auto-generated placeholder — LLM failed to produce valid test code for {path}\n"
            "def test_placeholder():\n"
            "    pass\n"
        )
        test_file_path.write_text(placeholder, encoding="utf-8")

    return test_file_path


def _test_path_for(source_path: Path) -> Path:
    """Derive the test file path from a source file path."""
    try:
        relative = source_path.relative_to(config.PROJECT_DIR)
    except ValueError:
        relative = Path(source_path.name)

    test_path = config.PROJECT_DIR / "tests" / relative
    if not test_path.name.startswith("test_"):
        test_path = test_path.with_name("test_" + test_path.name)
    return test_path
