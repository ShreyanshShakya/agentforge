"""
utils/json_parser.py
Robust JSON extraction from LLM output that may contain surrounding text.
"""

import json
import logging

logger = logging.getLogger(__name__)


def parse_json(text: str) -> dict:
    """
    Parse JSON from a string, tolerating leading/trailing LLM prose.

    Raises:
        ValueError if no valid JSON object can be extracted.
    """
    # Fast path: the whole string is valid JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Slow path: find the outermost { ... } block
    start = text.find("{")
    end   = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = text[start : end + 1]
        try:
            return json.loads(snippet)
        except json.JSONDecodeError as exc:
            logger.debug("JSON extraction failed: %s", exc)

    raise ValueError(f"No valid JSON object found in text (length={len(text)})")
