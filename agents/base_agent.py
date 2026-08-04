"""
agents/base_agent.py
Base class for all AgentForge agents.
Handles Ollama calls, MD5 caching, and cache-control flags.
"""

from ollama import chat
import time
import hashlib
import logging

import config

logger = logging.getLogger(__name__)


class BaseAgent:
    def __init__(
        self,
        name: str,
        system_prompt: str,
        model: str = config.DEFAULT_PLANNER_MODEL,
        num_predict: int = 500,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.model = model
        self.num_predict = num_predict

    # ── Cache helpers ──────────────────────────────────────────────────────────

    def _cache_path(self, task: str):
        key = hashlib.md5(
            f"{self.system_prompt}{task}".encode("utf-8")
        ).hexdigest()
        safe_name = self.name.replace(" ", "_")
        config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return config.CACHE_DIR / f"{safe_name}_{key}.txt"

    def _load_cache(self, task: str):
        path = self._cache_path(task)
        if path.exists():
            logger.debug("%s: cache hit (%s)", self.name, path.name)
            return path.read_text(encoding="utf-8")
        return None

    def _save_cache(self, task: str, content: str):
        self._cache_path(task).write_text(content, encoding="utf-8")

    def clear_cache(self):
        """Delete all cached responses for this agent."""
        safe_name = self.name.replace(" ", "_")
        deleted = 0
        for f in config.CACHE_DIR.glob(f"{safe_name}_*.txt"):
            f.unlink()
            deleted += 1
        logger.info("%s: cleared %d cache file(s)", self.name, deleted)

    # ── Main entry point ───────────────────────────────────────────────────────

    def run(self, task: str, use_cache: bool = True) -> str:
        """
        Run the agent on `task`.

        Args:
            task:      The prompt to send (user turn).
            use_cache: If False, always call the LLM and overwrite the cache.
        """
        if use_cache:
            cached = self._load_cache(task)
            if cached is not None:
                logger.info("%s: loaded from cache", self.name)
                return cached

        logger.info("%s: calling LLM (model=%s)", self.name, self.model)
        start = time.time()

        response = chat(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user",   "content": task},
            ],
            options={"num_predict": self.num_predict},
        )

        elapsed = time.time() - start
        logger.info("%s: completed in %.2fs", self.name, elapsed)

        content = response["message"]["content"]
        self._save_cache(task, content)
        return content
