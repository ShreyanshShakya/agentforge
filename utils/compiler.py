"""
utils/compiler.py
Python syntax validation using py_compile.
"""

import py_compile
from pathlib import Path


def check_python_file(path: str | Path) -> tuple[bool, str | None]:
    """
    Compile-check a Python file for syntax errors.

    Returns:
        (True, None)       on success
        (False, error_msg) on failure
    """
    try:
        py_compile.compile(str(path), doraise=True)
        return True, None
    except py_compile.PyCompileError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)
