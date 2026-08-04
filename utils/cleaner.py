"""
utils/cleaner.py
Centralises all regex-based LLM output cleaning so agents don't duplicate it.
"""

import re


def strip_markdown(code: str) -> str:
    """Remove markdown code fences and FILE:/END_FILE markers from LLM output."""
    code = re.sub(r"FILE:.*?\n", "", code)
    code = code.replace("END_FILE", "")
    code = re.sub(r"```[a-zA-Z]*\n?", "", code)
    code = re.sub(r"```\n?", "", code)
    return code.strip()
