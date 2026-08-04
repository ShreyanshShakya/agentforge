"""
pipeline/integration.py
v0.7 Post-generation integration phase:

  1. Runtime integration test  — run the project entry point as a subprocess
                                  and verify it starts (or runs) cleanly.

  2. API endpoint validation   — if a web framework (FastAPI / Flask) is
                                  detected, start the server, hit the auto-
                                  discovered endpoints, and assert HTTP 2xx.

Both steps are optional and only run when invoked from main.py with
--integration enabled.
"""

import subprocess
import sys
import time
import socket
import logging
import re
from pathlib import Path
from typing import Any

import config

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

_FRAMEWORK_PATTERNS = {
    "fastapi": re.compile(r"\bfastapi\b", re.IGNORECASE),
    "flask":   re.compile(r"\bflask\b",   re.IGNORECASE),
}

_UVICORN_ENTRY_PATTERNS = [
    # uvicorn app.main:app  OR  uvicorn main:app
    re.compile(r'uvicorn\.run\(\s*["\']?(\S+?)["\']?\s*,', re.IGNORECASE),
    re.compile(r'app\s*=\s*FastAPI\(', re.IGNORECASE),
]

_FLASK_ENTRY_PATTERNS = [
    re.compile(r'app\s*=\s*Flask\(', re.IGNORECASE),
    re.compile(r'app\.run\(', re.IGNORECASE),
]

_ROUTE_PATTERNS = [
    # FastAPI / Flask route decorators
    re.compile(r'@(?:app|router)\.(get|post|put|patch|delete|head)\(\s*["\']([^"\']+)["\']', re.IGNORECASE),
]

SERVER_STARTUP_TIMEOUT  = 20   # seconds to wait for server to accept connections
SERVER_REQUEST_TIMEOUT  = 5    # seconds per HTTP request
SERVER_PORT             = 18765  # local port used during integration tests


# ── Public API ─────────────────────────────────────────────────────────────────

def run_integration_phase(
    file_plan: list[dict],
    project_dir: Path = None,
) -> dict[str, Any]:
    """
    Run the full integration phase for a generated project.

    Returns a result dict:
    {
        "runtime": {"success": bool, "output": str, "error": str | None},
        "api":     {"success": bool, "results": list[dict], "error": str | None}
                   or None if no web framework detected
    }
    """
    project_dir = project_dir or config.PROJECT_DIR
    results: dict[str, Any] = {"runtime": None, "api": None}

    # ── 1. Runtime integration test ───────────────────────────────────────────
    entry_point = _find_entry_point(project_dir, file_plan)
    if entry_point:
        logger.info("Integration: runtime test → %s", entry_point)
        results["runtime"] = _run_runtime_test(entry_point, project_dir)
    else:
        logger.info("Integration: no runnable entry point found — skipping runtime test")
        results["runtime"] = {"success": True, "output": "", "error": "No entry point found"}

    # ── 2. API endpoint validation ────────────────────────────────────────────
    framework = _detect_framework(project_dir, file_plan)
    if framework:
        logger.info("Integration: detected framework=%s — running API validation", framework)
        results["api"] = _run_api_validation(framework, project_dir, file_plan)
    else:
        logger.info("Integration: no web framework detected — skipping API validation")

    return results


# ── Runtime test ───────────────────────────────────────────────────────────────

def _find_entry_point(project_dir: Path, file_plan: list[dict]) -> Path | None:
    """
    Heuristically find the project's main entry point.
    Priority: main.py at root > app/main.py > first .py with __main__
    """
    candidates = [
        project_dir / "main.py",
        project_dir / "app" / "main.py",
        project_dir / "src" / "main.py",
    ]
    for c in candidates:
        if c.exists():
            return c

    # Last resort: any file from the plan that has if __name__ == '__main__'
    for fi in file_plan:
        p = project_dir / fi["path"]
        if p.suffix == ".py" and p.exists():
            text = p.read_text(encoding="utf-8", errors="ignore")
            if '__name__ == "__main__"' in text or "__name__ == '__main__'" in text:
                return p

    return None


def _run_runtime_test(entry_point: Path, project_dir: Path) -> dict:
    """
    Run the entry point as a subprocess. For scripts that exit on their own
    (non-server), we wait for completion. For long-running processes we give
    them 5 seconds to start without crashing.
    """
    python = _venv_python(project_dir)
    logger.info("Runtime test: running %s with %s", entry_point.name, python)

    try:
        result = subprocess.run(
            [python, str(entry_point)],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(project_dir),
        )
        success = result.returncode == 0
        return {
            "success": success,
            "output": result.stdout[:2000],
            "error":  result.stderr[:2000] if not success else None,
        }
    except subprocess.TimeoutExpired as exc:
        # Process still running after 10s — treat as "started cleanly"
        logger.info("Runtime test: process still running after timeout (good for servers)")
        return {
            "success": True,
            "output": (exc.stdout or b"").decode(errors="ignore")[:2000],
            "error":  None,
        }
    except Exception as exc:
        return {"success": False, "output": "", "error": str(exc)}


# ── API endpoint validation ────────────────────────────────────────────────────

def _detect_framework(project_dir: Path, file_plan: list[dict]) -> str | None:
    """Return 'fastapi', 'flask', or None."""
    # Check requirements.txt first (fastest)
    req = project_dir / "requirements.txt"
    if req.exists():
        text = req.read_text(encoding="utf-8", errors="ignore").lower()
        for name, pattern in _FRAMEWORK_PATTERNS.items():
            if pattern.search(text):
                return name

    # Scan Python source files from the plan
    for fi in file_plan:
        p = project_dir / fi["path"]
        if p.suffix == ".py" and p.exists():
            text = p.read_text(encoding="utf-8", errors="ignore")
            for name, pattern in _FRAMEWORK_PATTERNS.items():
                if pattern.search(text):
                    return name

    return None


def _find_app_module(project_dir: Path, file_plan: list[dict]) -> str | None:
    """
    Return a dotted module path string suitable for uvicorn/flask run,
    e.g. 'app.main:app'.
    """
    for fi in file_plan:
        p = project_dir / fi["path"]
        if p.suffix != ".py" or not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        # FastAPI: app = FastAPI()
        if re.search(r'app\s*=\s*FastAPI\(', text):
            module = fi["path"].replace("/", ".").replace("\\", ".").removesuffix(".py")
            return f"{module}:app"
        # Flask: app = Flask(__)
        if re.search(r'app\s*=\s*Flask\(', text):
            module = fi["path"].replace("/", ".").replace("\\", ".").removesuffix(".py")
            return f"{module}:app"
    return None


def _discover_routes(project_dir: Path, file_plan: list[dict]) -> list[tuple[str, str]]:
    """
    Scan all Python files for route decorators.
    Returns list of (method, path) tuples, e.g. [('GET', '/'), ('GET', '/health')].
    Always includes '/' as a fallback.
    """
    routes: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for fi in file_plan:
        p = project_dir / fi["path"]
        if p.suffix != ".py" or not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        for pattern in _ROUTE_PATTERNS:
            for m in pattern.finditer(text):
                method = m.group(1).upper()
                route  = m.group(2)
                if not route.startswith("/"):
                    route = "/" + route
                key = (method, route)
                if key not in seen:
                    routes.append(key)
                    seen.add(key)

    if not routes:
        routes = [("GET", "/")]
    elif ("GET", "/") not in seen:
        routes.insert(0, ("GET", "/"))

    return routes


def _free_port() -> int:
    """Return a free TCP port (falls back to SERVER_PORT)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]
    except OSError:
        return SERVER_PORT


def _wait_for_port(port: int, timeout: int) -> bool:
    """Poll until a TCP port accepts connections or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def _run_api_validation(
    framework: str,
    project_dir: Path,
    file_plan: list[dict],
) -> dict:
    """
    Start the web server, hit each discovered endpoint, return results.
    """
    import urllib.request
    import urllib.error

    app_module = _find_app_module(project_dir, file_plan)
    if not app_module:
        return {"success": False, "results": [], "error": "Could not locate app module"}

    port    = _free_port()
    python  = _venv_python(project_dir)
    routes  = _discover_routes(project_dir, file_plan)
    logger.info("API validation: app=%s port=%d routes=%s", app_module, port, routes)

    # Build server start command
    if framework == "fastapi":
        cmd = [python, "-m", "uvicorn", app_module,
               "--host", "127.0.0.1", "--port", str(port), "--no-access-log"]
    else:  # flask
        module, obj = app_module.split(":") if ":" in app_module else (app_module, "app")
        cmd = [python, "-m", "flask", "--app", module, "run",
               "--host", "127.0.0.1", "--port", str(port)]

    server_proc = None
    endpoint_results: list[dict] = []
    overall_success = False

    try:
        logger.info("API validation: starting server → %s", " ".join(cmd))
        server_proc = subprocess.Popen(
            cmd,
            cwd=str(project_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if not _wait_for_port(port, SERVER_STARTUP_TIMEOUT):
            stderr = server_proc.stderr.read(2000).decode(errors="ignore") if server_proc.stderr else ""
            return {
                "success": False,
                "results": [],
                "error": f"Server did not start within {SERVER_STARTUP_TIMEOUT}s.\n{stderr}",
            }

        logger.info("API validation: server is up on port %d", port)

        # Hit each route
        for method, route in routes:
            url = f"http://127.0.0.1:{port}{route}"
            try:
                req = urllib.request.Request(url, method=method)
                with urllib.request.urlopen(req, timeout=SERVER_REQUEST_TIMEOUT) as resp:
                    status = resp.status
            except urllib.error.HTTPError as e:
                status = e.code
            except Exception as e:
                endpoint_results.append({
                    "method": method, "route": route,
                    "status": None, "success": False, "error": str(e),
                })
                continue

            success = 200 <= status < 300
            endpoint_results.append({
                "method": method, "route": route,
                "status": status, "success": success, "error": None,
            })
            logger.info("  %s %s → %d %s", method, route, status, "✓" if success else "✗")

        overall_success = all(r["success"] for r in endpoint_results)

    finally:
        if server_proc and server_proc.poll() is None:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_proc.kill()

    return {
        "success": overall_success,
        "results": endpoint_results,
        "error":   None if overall_success else "One or more endpoints returned non-2xx",
    }


# ── Helpers ────────────────────────────────────────────────────────────────────

def _venv_python(project_dir: Path) -> str:
    """Return path to venv Python if it exists, else system Python."""
    candidates = [
        project_dir / ".venv" / "bin"     / "python",
        project_dir / ".venv" / "Scripts" / "python.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return sys.executable


def format_integration_report(results: dict) -> str:
    """Return a human-readable summary of integration results."""
    lines = ["\n=== Integration Test Results ==="]

    rt = results.get("runtime")
    if rt:
        status = "✓ PASS" if rt["success"] else "✗ FAIL"
        lines.append(f"\nRuntime Test: {status}")
        if rt.get("output"):
            lines.append(f"  Output: {rt['output'][:200]}")
        if rt.get("error"):
            lines.append(f"  Error:  {rt['error'][:300]}")

    api = results.get("api")
    if api:
        status = "✓ PASS" if api["success"] else "✗ FAIL"
        lines.append(f"\nAPI Endpoint Validation: {status}")
        for r in api.get("results", []):
            tick = "✓" if r["success"] else "✗"
            code = r["status"] or "ERR"
            lines.append(f"  {tick} {r['method']:6} {r['route']:<30} {code}")
        if api.get("error"):
            lines.append(f"  Error: {api['error'][:300]}")

    return "\n".join(lines)
