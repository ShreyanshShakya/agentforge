"""
agents/dependency_agent.py
Dependency Resolution Agent — installs the generated project's requirements.txt
into an isolated virtual environment inside PROJECT_DIR before tests run.
"""

import subprocess
import sys
import logging
from pathlib import Path

import config

logger = logging.getLogger(__name__)


def resolve_dependencies(project_dir: Path = None) -> tuple[bool, str | None]:
    """
    Find and install requirements.txt from the generated project.

    Creates a virtual environment at PROJECT_DIR/.venv so installs are
    isolated from the host Python and from run to run.

    Returns:
        (True, None)         — all packages installed successfully
        (False, error_str)   — installation failed; error_str is the pip output
    """
    project_dir = project_dir or config.PROJECT_DIR

    req_file = project_dir / "requirements.txt"
    if not req_file.exists():
        logger.info("DependencyAgent: no requirements.txt found — skipping install")
        return True, None

    venv_dir = project_dir / ".venv"

    # ── Create venv if it doesn't exist ───────────────────────────────────────
    if not venv_dir.exists():
        logger.info("DependencyAgent: creating venv at %s", venv_dir)
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            msg = f"venv creation failed:\n{result.stderr}"
            logger.error("DependencyAgent: %s", msg)
            return False, msg

    # ── Locate pip inside the venv ────────────────────────────────────────────
    if (venv_dir / "bin" / "pip").exists():
        pip = str(venv_dir / "bin" / "pip")       # Linux / macOS
    elif (venv_dir / "Scripts" / "pip.exe").exists():
        pip = str(venv_dir / "Scripts" / "pip.exe")  # Windows
    else:
        pip = str(venv_dir / "bin" / "pip")        # fallback

    # ── Install requirements ──────────────────────────────────────────────────
    logger.info("DependencyAgent: installing %s", req_file)
    result = subprocess.run(
        [pip, "install", "-r", str(req_file), "--quiet"],
        capture_output=True,
        text=True,
        timeout=config.SUBPROCESS_TIMEOUT * 5,   # allow longer for downloads
        cwd=str(project_dir),
    )

    if result.returncode != 0:
        msg = (
            f"pip install failed (exit {result.returncode}):\n"
            f"{result.stderr}\n{result.stdout}"
        )
        logger.error("DependencyAgent: %s", msg)
        return False, msg

    logger.info("DependencyAgent: all dependencies installed successfully")
    return True, None
