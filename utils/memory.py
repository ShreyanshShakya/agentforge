"""
utils/memory.py
Long-term project memory with vector embeddings for cross-run learning.
"""

import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta

import config

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A single memory entry with embedding."""
    id: str
    timestamp: float
    project_id: str
    category: str  # "decision", "code_pattern", "error_fix", "architecture", "requirement"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: List[float] = field(default_factory=list)
    access_count: int = 0
    last_accessed: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        return cls(**data)


class MemoryStore:
    """
    Persistent memory store with vector embeddings for semantic retrieval.
    Uses Ollama for embeddings (nomic-embed-text by default).
    """

    def __init__(self, project_id: str = None):
        self.project_id = project_id or self._generate_project_id()
        self.memory_file = config.MEMORY_DIR / f"{self.project_id}.jsonl"
        self.index_file = config.MEMORY_DIR / f"{self.project_id}_index.json"
        self.entries: Dict[str, MemoryEntry] = {}
        self._load()

    def _generate_project_id(self) -> str:
        return hashlib.md5(str(time.time()).encode()).hexdigest()[:12]

    def _load(self):
        """Load memory entries from disk."""
        if self.memory_file.exists():
            with open(self.memory_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        entry = MemoryEntry.from_dict(data)
                        self.entries[entry.id] = entry
                    except json.JSONDecodeError:
                        continue
        logger.info("Loaded %d memory entries for project %s", len(self.entries), self.project_id)

        # Cleanup old entries
        self._cleanup_old_entries()

    def _save(self):
        """Save all entries to disk (append-only for durability)."""
        with open(self.memory_file, "w", encoding="utf-8") as f:
            for entry in self.entries.values():
                f.write(json.dumps(entry.to_dict()) + "\n")
        # Save index
        index = {
            "project_id": self.project_id,
            "entry_count": len(self.entries),
            "categories": list(set(e.category for e in self.entries.values())),
            "updated": time.time(),
        }
        self.index_file.write_text(json.dumps(index, indent=2), encoding="utf-8")

    def _cleanup_old_entries(self):
        """Remove entries older than TTL and enforce max entries."""
        if not config.MEMORY_AUTO_SAVE:
            return

        cutoff = time.time() - (config.MEMORY_TTL_DAYS * 86400)
        to_remove = [
            eid for eid, entry in self.entries.items()
            if entry.timestamp < cutoff
        ]
        for eid in to_remove:
            del self.entries[eid]

        # Enforce max entries (keep most recently accessed)
        if len(self.entries) > config.MEMORY_MAX_ENTRIES:
            sorted_entries = sorted(
                self.entries.items(),
                key=lambda x: x[1].last_accessed or x[1].timestamp,
                reverse=True
            )
            self.entries = dict(sorted_entries[:config.MEMORY_MAX_ENTRIES])

        if to_remove or len(self.entries) > config.MEMORY_MAX_ENTRIES:
            self._save()

    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for text using Ollama."""
        try:
            from ollama import embeddings
            response = embeddings(model=config.MEMORY_EMBEDDINGS_MODEL, prompt=text)
            return response.get("embedding", [])
        except Exception as e:
            logger.warning("Failed to get embedding: %s", e)
            return []

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def add(
        self,
        category: str,
        content: str,
        metadata: Dict[str, Any] = None,
        embedding: List[float] = None
    ) -> str:
        """Add a new memory entry."""
        entry_id = hashlib.md5(f"{self.project_id}{category}{content}{time.time()}".encode()).hexdigest()[:16]

        if embedding is None:
            embedding = self._get_embedding(content)

        entry = MemoryEntry(
            id=entry_id,
            timestamp=time.time(),
            project_id=self.project_id,
            category=category,
            content=content,
            metadata=metadata or {},
            embedding=embedding,
        )

        self.entries[entry_id] = entry

        if config.MEMORY_AUTO_SAVE:
            self._save()

        logger.debug("Added memory entry: %s (%s)", entry_id, category)
        return entry_id

    def search(
        self,
        query: str,
        category: str = None,
        top_k: int = 5,
        min_similarity: float = None
    ) -> List[Tuple[MemoryEntry, float]]:
        """Search memory by semantic similarity."""
        if not self.entries:
            return []

        query_embedding = self._get_embedding(query)
        if not query_embedding:
            # Fallback to keyword search
            return self._keyword_search(query, category, top_k)

        min_sim = min_similarity or config.MEMORY_SIMILARITY_THRESHOLD
        results = []

        for entry in self.entries.values():
            if category and entry.category != category:
                continue
            if not entry.embedding:
                continue

            similarity = self._cosine_similarity(query_embedding, entry.embedding)
            if similarity >= min_sim:
                results.append((entry, similarity))

        results.sort(key=lambda x: x[1], reverse=True)

        # Update access stats
        for entry, _ in results[:top_k]:
            entry.access_count += 1
            entry.last_accessed = time.time()

        if config.MEMORY_AUTO_SAVE:
            self._save()

        return results[:top_k]

    def _keyword_search(self, query: str, category: str, top_k: int) -> List[Tuple[MemoryEntry, float]]:
        """Fallback keyword-based search."""
        query_terms = set(query.lower().split())
        results = []

        for entry in self.entries.values():
            if category and entry.category != category:
                continue

            content_terms = set(entry.content.lower().split())
            overlap = len(query_terms & content_terms)
            if overlap > 0:
                score = overlap / max(len(query_terms), 1)
                results.append((entry, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def get_recent(self, category: str = None, limit: int = 10) -> List[MemoryEntry]:
        """Get most recent entries, optionally filtered by category."""
        entries = list(self.entries.values())
        if category:
            entries = [e for e in entries if e.category == category]
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries[:limit]

    def get_by_category(self, category: str) -> List[MemoryEntry]:
        """Get all entries for a category."""
        return [e for e in self.entries.values() if e.category == category]

    def get_context_for_task(self, task: str, max_entries: int = 20) -> str:
        """Build a context string from relevant memories for a task."""
        # Search across key categories
        categories = ["decision", "architecture", "code_pattern", "error_fix", "requirement"]
        all_results = []

        for cat in categories:
            results = self.search(task, category=cat, top_k=5)
            all_results.extend(results)

        # Deduplicate and sort by relevance
        seen = set()
        unique = []
        for entry, score in sorted(all_results, key=lambda x: x[1], reverse=True):
            if entry.id not in seen:
                seen.add(entry.id)
                unique.append((entry, score))

        if not unique:
            return ""

        lines = [f"# Relevant Project Memory (Project: {self.project_id})"]
        for entry, score in unique[:max_entries]:
            meta = f" [{entry.category}]" + (f" {entry.metadata}" if entry.metadata else "")
            lines.append(f"\n## {entry.timestamp:.0f}{meta} (relevance: {score:.2f})")
            lines.append(entry.content[:1500])

        return "\n".join(lines)

    def export(self, filepath: Path):
        """Export memory to a portable JSON file."""
        data = {
            "project_id": self.project_id,
            "exported": datetime.now().isoformat(),
            "entries": [e.to_dict() for e in self.entries.values()],
        }
        filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def import_memory(self, filepath: Path, merge: bool = True):
        """Import memory from exported file."""
        data = json.loads(filepath.read_text(encoding="utf-8"))
        imported = 0
        for entry_data in data.get("entries", []):
            entry = MemoryEntry.from_dict(entry_data)
            if merge and entry.id in self.entries:
                continue
            self.entries[entry.id] = entry
            imported += 1
        self._save()
        logger.info("Imported %d memory entries", imported)

    def stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        cats = {}
        for e in self.entries.values():
            cats[e.category] = cats.get(e.category, 0) + 1
        return {
            "project_id": self.project_id,
            "total_entries": len(self.entries),
            "categories": cats,
            "oldest": min((e.timestamp for e in self.entries.values()), default=0),
            "newest": max((e.timestamp for e in self.entries.values()), default=0),
        }


# Global memory store instance (lazy initialization)
_memory_store: Optional[MemoryStore] = None


def get_memory_store(project_id: str = None) -> MemoryStore:
    """Get or create the global memory store."""
    global _memory_store
    if _memory_store is None or (project_id and _memory_store.project_id != project_id):
        _memory_store = MemoryStore(project_id)
    return _memory_store


def remember_decision(project_id: str, decision: str, rationale: str, context: str = "") -> str:
    """Record a design/architecture decision."""
    store = get_memory_store(project_id)
    return store.add(
        category="decision",
        content=f"Decision: {decision}\nRationale: {rationale}\nContext: {context}",
        metadata={"type": "decision", "decision": decision, "rationale": rationale}
    )


def remember_code_pattern(project_id: str, pattern: str, language: str, description: str) -> str:
    """Record a reusable code pattern."""
    store = get_memory_store(project_id)
    return store.add(
        category="code_pattern",
        content=f"Language: {language}\nPattern: {pattern}\nDescription: {description}",
        metadata={"type": "code_pattern", "language": language}
    )


def remember_error_fix(project_id: str, error: str, fix: str, file_path: str = "") -> str:
    """Record an error and its fix for future reference."""
    store = get_memory_store(project_id)
    return store.add(
        category="error_fix",
        content=f"Error: {error}\nFix: {fix}\nFile: {file_path}",
        metadata={"type": "error_fix", "file": file_path}
    )


def remember_architecture(project_id: str, architecture: str, components: List[str] = None) -> str:
    """Record architecture decisions."""
    store = get_memory_store(project_id)
    return store.add(
        category="architecture",
        content=f"Architecture: {architecture}\nComponents: {components or []}",
        metadata={"type": "architecture", "components": components or []}
    )


def remember_requirement(project_id: str, requirement: str, priority: str = "medium") -> str:
    """Record a project requirement."""
    store = get_memory_store(project_id)
    return store.add(
        category="requirement",
        content=f"Requirement: {requirement}\nPriority: {priority}",
        metadata={"type": "requirement", "priority": priority}
    )


def recall_relevant(project_id: str, query: str, max_entries: int = 15) -> str:
    """Recall relevant memories for a query."""
    store = get_memory_store(project_id)
    return store.get_context_for_task(query, max_entries=max_entries)