import pytest
import sys
import os
from unittest.mock import patch
import importlib

# Ensure project root is on sys.path so `app.hello_world` is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def test_prints_hello_world(capsys):
    """The script outputs 'Hello, World!' to stdout when executed."""
    import app.hello_world  # noqa: F401 — importing executes the top-level code
    captured = capsys.readouterr()
    assert "Hello, World!" in captured.out


def test_handles_exception_gracefully():
    """When print() raises, the except block catches it and prints an error message."""
    call_count = {"n": 0}

    def patched_print(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise Exception("simulated failure")

    with patch("builtins.print", side_effect=patched_print):
        # Reload so the module-level code runs again with patched print
        import app.hello_world
        importlib.reload(app.hello_world)

    # Both the try-print and the except-print must have been called
    assert call_count["n"] == 2
