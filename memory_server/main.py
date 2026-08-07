"""
memory_server/main.py
Central Memory Server for Team Memory Sharing
FastAPI-based server with WebSocket support for real-time sync
"""

import asyncio
import json
import logging
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict, field
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Server settings"""
    host: str = "0.0.0.0"
    port: int = 8081
    data_dir: str = "./memory_data"
    max_entries_per_project: int = 50000
    sync_interval: int = 5  # seconds
    enable_auth: bool = False
    secret_key: str = "change-me-in-production"

    class Config:
        env_file = ".env"


settings = Settings()

# Ensure data directory exists
DATA_DIR = Path(settings.data_dir)
DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class MemoryEntry:
    """A memory entry with vector embedding"""
    id: str
    project_id: str
    category: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: List[float] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 1
    author: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        return cls(**data)


@dataclass
class ProjectMemory:
    """Memory store for a single project"""
    project_id: str
    entries: Dict[str, MemoryEntry] = field(default_factory=dict)
    subscribers: Set[WebSocket] = field(default_factory=set)
    last_sync: float = field(default_factory=time.time)
    version: int = 0


class MemoryServer:
    """Central memory server with multi-project support"""

    def __init__(self):
        self.projects: Dict[str, ProjectMemory] = {}
        self.global_subscribers: Set[WebSocket] = set()
        self._load_all_projects()

    def _load_all_projects(self):
        """Load all projects from disk"""
        for project_file in DATA_DIR.glob("*.jsonl"):
            project_id = project_file.stem
            self._load_project(project_id)

    def _load_project(self, project_id: str):
        """Load a single project from disk"""
        project_file = DATA_DIR / f"{project_id}.jsonl"
        if not project_file.exists():
            return

        project = ProjectMemory(project_id=project_id)
        try:
            with open(project_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        entry = MemoryEntry.from_dict(data)
                        project.entries[entry.id] = entry
                    except json.JSONDecodeError:
                        continue
            project.version = len(project.entries)
            self.projects[project_id] = project
            logger.info(f"Loaded project {project_id}: {len(project.entries)} entries")
        except Exception as e:
            logger.error(f"Failed to load project {project_id}: {e}")

    def _save_project(self, project_id: str):
        """Save a project to disk"""
        project = self.projects.get(project_id)
        if not project:
            return

        project_file = DATA_DIR / f"{project_id}.jsonl"
        try:
            with open(project_file, "w", encoding="utf-8") as f:
                for entry in project.entries.values():
                    f.write(json.dumps(entry.to_dict()) + "\n")
            project.last_sync = time.time()
        except Exception as e:
            logger.error(f"Failed to save project {project_id}: {e}")

    def get_or_create_project(self, project_id: str) -> ProjectMemory:
        """Get or create a project"""
        if project_id not in self.projects:
            self.projects[project_id] = ProjectMemory(project_id=project_id)
        return self.projects[project_id]

    def add_entry(self, project_id: str, entry: MemoryEntry) -> MemoryEntry:
        """Add or update a memory entry"""
        project = self.get_or_create_project(project_id)
        entry.project_id = project_id
        entry.updated_at = time.time()
        entry.version = project.version + 1
        project.entries[entry.id] = entry
        project.version += 1
        self._save_project(project_id)
        return entry

    def get_entry(self, project_id: str, entry_id: str) -> Optional[MemoryEntry]:
        """Get a specific entry"""
        project = self.projects.get(project_id)
        if not project:
            return None
        return project.entries.get(entry_id)

    def delete_entry(self, project_id: str, entry_id: str) -> bool:
        """Delete an entry"""
        project = self.projects.get(project_id)
        if not project or entry_id not in project.entries:
            return False
        del project.entries[entry_id]
        project.version += 1
        self._save_project(project_id)
        return True

    def search(self, project_id: str, query: str, category: str = None,
               top_k: int = 10, min_similarity: float = 0.75) -> List[tuple]:
        """Search entries by semantic similarity (fallback to keyword)"""
        project = self.projects.get(project_id)
        if not project or not project.entries:
            return []

        # Try vector search first
        query_embedding = self._get_embedding(query)
        if query_embedding:
            results = []
            for entry in project.entries.values():
                if category and entry.category != category:
                    continue
                if not entry.embedding:
                    continue
                similarity = self._cosine_similarity(query_embedding, entry.embedding)
                if similarity >= min_similarity:
                    results.append((entry, similarity))
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]

        # Fallback to keyword search
        return self._keyword_search(project, query, category, top_k)

    def _keyword_search(self, project: ProjectMemory, query: str,
                        category: str, top_k: int) -> List[tuple]:
        """Keyword-based search fallback"""
        query_terms = set(query.lower().split())
        results = []
        for entry in project.entries.values():
            if category and entry.category != category:
                continue
            content_terms = set(entry.content.lower().split())
            overlap = len(query_terms & content_terms)
            if overlap > 0:
                score = overlap / max(len(query_terms), 1)
                results.append((entry, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding from Ollama"""
        try:
            import httpx
            import os
            ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
            response = httpx.post(
                f"{ollama_host}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text},
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get("embedding")
        except Exception as e:
            logger.warning(f"Failed to get embedding: {e}")
        return None

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity"""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def list_entries(self, project_id: str, category: str = None,
                     limit: int = 100, offset: int = 0) -> List[MemoryEntry]:
        """List entries with pagination"""
        project = self.projects.get(project_id)
        if not project:
            return []

        entries = list(project.entries.values())
        if category:
            entries = [e for e in entries if e.category == category]
        entries.sort(key=lambda e: e.updated_at, reverse=True)
        return entries[offset:offset + limit]

    def get_stats(self, project_id: str) -> Dict[str, Any]:
        """Get project statistics"""
        project = self.projects.get(project_id)
        if not project:
            return {"project_id": project_id, "entries": 0, "categories": {}}

        cats = {}
        for e in project.entries.values():
            cats[e.category] = cats.get(e.category, 0) + 1

        return {
            "project_id": project_id,
            "entries": len(project.entries),
            "categories": cats,
            "version": project.version,
            "last_sync": project.last_sync
        }

    async def subscribe(self, project_id: str, websocket: WebSocket):
        """Subscribe to project updates"""
        project = self.get_or_create_project(project_id)
        project.subscribers.add(websocket)
        self.global_subscribers.add(websocket)

    async def unsubscribe(self, project_id: str, websocket: WebSocket):
        """Unsubscribe from project updates"""
        project = self.projects.get(project_id)
        if project:
            project.subscribers.discard(websocket)
        self.global_subscribers.discard(websocket)

    async def broadcast_to_project(self, project_id: str, message: dict):
        """Broadcast message to all project subscribers"""
        project = self.projects.get(project_id)
        if not project:
            return

        disconnected = []
        for ws in project.subscribers:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            await self.unsubscribe(project_id, ws)

    async def broadcast_global(self, message: dict):
        """Broadcast to all global subscribers"""
        disconnected = []
        for ws in self.global_subscribers:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.global_subscribers.discard(ws)


# Global server instance
memory_server = MemoryServer()


# Pydantic models
class EntryCreate(BaseModel):
    category: str
    content: str
    metadata: Dict[str, Any] = {}
    author: str = "api"


class EntryUpdate(BaseModel):
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    category: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    category: Optional[str] = None
    top_k: int = 10
    min_similarity: float = 0.75


class SyncRequest(BaseModel):
    entries: List[Dict[str, Any]]
    project_id: str


# FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Memory Server starting up")
    yield
    logger.info("Memory Server shutting down")


app = FastAPI(
    title="AgentForge Memory Server",
    version="1.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Routes
@app.get("/health")
async def health():
    return {"status": "healthy", "projects": len(memory_server.projects)}


@app.get("/api/projects")
async def list_projects():
    return {
        "projects": [
            memory_server.get_stats(pid)
            for pid in memory_server.projects.keys()
        ]
    }


@app.post("/api/projects/{project_id}/entries")
async def create_entry(project_id: str, entry_data: EntryCreate):
    project = memory_server.get_or_create_project(project_id)

    entry_id = hashlib.md5(
        f"{project_id}{entry_data.category}{entry_data.content}{time.time()}".encode()
    ).hexdigest()[:16]

    entry = MemoryEntry(
        id=entry_id,
        project_id=project_id,
        category=entry_data.category,
        content=entry_data.content,
        metadata=entry_data.metadata,
        author=entry_data.author
    )

    # Get embedding
    entry.embedding = memory_server._get_embedding(entry_data.content) or []

    saved = memory_server.add_entry(project_id, entry)

    # Broadcast to subscribers
    await memory_server.broadcast_to_project(project_id, {
        "type": "entry_created",
        "project_id": project_id,
        "entry": saved.to_dict()
    })

    return saved.to_dict()


@app.get("/api/projects/{project_id}/entries")
async def list_entries(project_id: str, category: str = None,
                       limit: int = 100, offset: int = 0):
    entries = memory_server.list_entries(project_id, category, limit, offset)
    return {"entries": [e.to_dict() for e in entries]}


@app.get("/api/projects/{project_id}/entries/{entry_id}")
async def get_entry(project_id: str, entry_id: str):
    entry = memory_server.get_entry(project_id, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry.to_dict()


@app.patch("/api/projects/{project_id}/entries/{entry_id}")
async def update_entry(project_id: str, entry_id: str, update: EntryUpdate):
    project = memory_server.projects.get(project_id)
    if not project or entry_id not in project.entries:
        raise HTTPException(status_code=404, detail="Entry not found")

    entry = project.entries[entry_id]
    if update.content is not None:
        entry.content = update.content
        entry.embedding = memory_server._get_embedding(update.content) or []
    if update.metadata is not None:
        entry.metadata.update(update.metadata)
    if update.category is not None:
        entry.category = update.category

    entry.updated_at = time.time()
    entry.version += 1
    project.version += 1
    memory_server._save_project(project_id)

    await memory_server.broadcast_to_project(project_id, {
        "type": "entry_updated",
        "project_id": project_id,
        "entry": entry.to_dict()
    })

    return entry.to_dict()


@app.delete("/api/projects/{project_id}/entries/{entry_id}")
async def delete_entry(project_id: str, entry_id: str):
    success = memory_server.delete_entry(project_id, entry_id)
    if not success:
        raise HTTPException(status_code=404, detail="Entry not found")

    await memory_server.broadcast_to_project(project_id, {
        "type": "entry_deleted",
        "project_id": project_id,
        "entry_id": entry_id
    })

    return {"success": True}


@app.post("/api/projects/{project_id}/search")
async def search_entries(project_id: str, request: SearchRequest):
    results = memory_server.search(
        project_id, request.query, request.category,
        request.top_k, request.min_similarity
    )
    return {
        "results": [
            {"entry": entry.to_dict(), "score": score}
            for entry, score in results
        ]
    }


@app.get("/api/projects/{project_id}/stats")
async def get_project_stats(project_id: str):
    return memory_server.get_stats(project_id)


@app.post("/api/projects/{project_id}/sync")
async def sync_project(project_id: str, request: SyncRequest):
    """Sync entries from a client (for offline-first clients)"""
    project = memory_server.get_or_create_project(project_id)
    synced = 0
    conflicts = []

    for entry_data in request.entries:
        entry_id = entry_data.get("id")
        if not entry_id:
            continue

        existing = project.entries.get(entry_id)
        if existing:
            # Check version for conflicts
            if entry_data.get("version", 0) < existing.version:
                conflicts.append({
                    "entry_id": entry_id,
                    "server_version": existing.version,
                    "client_version": entry_data.get("version", 0)
                })
                continue

        entry = MemoryEntry.from_dict(entry_data)
        entry.project_id = project_id
        project.entries[entry_id] = entry
        synced += 1

    project.version += synced
    memory_server._save_project(project_id)

    await memory_server.broadcast_to_project(project_id, {
        "type": "sync_completed",
        "project_id": project_id,
        "synced": synced,
        "conflicts": conflicts
    })

    return {"synced": synced, "conflicts": conflicts}


# WebSocket endpoint
@app.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    await websocket.accept()
    await memory_server.subscribe(project_id, websocket)

    try:
        # Send initial sync
        await websocket.send_json({
            "type": "connected",
            "project_id": project_id,
            "version": memory_server.projects.get(project_id, ProjectMemory(project_id)).version
        })

        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                await handle_ws_message(websocket, project_id, msg)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await memory_server.unsubscribe(project_id, websocket)


async def handle_ws_message(websocket: WebSocket, project_id: str, msg: dict):
    """Handle incoming WebSocket messages"""
    msg_type = msg.get("type")

    if msg_type == "ping":
        await websocket.send_json({"type": "pong"})

    elif msg_type == "subscribe":
        # Already subscribed on connect
        pass

    elif msg_type == "create_entry":
        entry_data = EntryCreate(**msg.get("data", {}))
        # Reuse the create_entry logic
        project = memory_server.get_or_create_project(project_id)
        entry_id = hashlib.md5(
            f"{project_id}{entry_data.category}{entry_data.content}{time.time()}".encode()
        ).hexdigest()[:16]

        entry = MemoryEntry(
            id=entry_id,
            project_id=project_id,
            category=entry_data.category,
            content=entry_data.content,
            metadata=entry_data.metadata,
            author=entry_data.author
        )
        entry.embedding = memory_server._get_embedding(entry_data.content) or []
        saved = memory_server.add_entry(project_id, entry)

        await websocket.send_json({
            "type": "entry_created",
            "project_id": project_id,
            "entry": saved.to_dict()
        })

    elif msg_type == "search":
        request = SearchRequest(**msg.get("data", {}))
        results = memory_server.search(
            project_id, request.query, request.category,
            request.top_k, request.min_similarity
        )
        await websocket.send_json({
            "type": "search_results",
            "request_id": msg.get("request_id"),
            "results": [
                {"entry": entry.to_dict(), "score": score}
                for entry, score in results
            ]
        })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)