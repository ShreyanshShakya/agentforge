"""
webui/main.py - Web UI for monitoring autonomous agent progress
FastAPI + WebSocket for real-time updates
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.autonomous_agent import AutonomousAgent, Goal, GoalStatus, Task
from utils.memory import get_memory_store

logger = logging.getLogger(__name__)

app = FastAPI(title="AgentForge Web UI", version="1.1.0")

# Static files and templates
WEBUI_DIR = Path(__file__).parent
STATIC_DIR = WEBUI_DIR / "static"
TEMPLATES_DIR = WEBUI_DIR / "templates"

STATIC_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Global state for connected WebSocket clients
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.agent: Optional[AutonomousAgent] = None
        self.broadcast_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)

    def set_agent(self, agent: AutonomousAgent):
        self.agent = agent
        if self.broadcast_task:
            self.broadcast_task.cancel()
        self.broadcast_task = asyncio.create_task(self._broadcast_loop())

    async def _broadcast_loop(self):
        """Periodically broadcast agent status to all connected clients"""
        while self.agent and self.agent.running:
            try:
                status = self.agent.get_status()
                await self.broadcast({
                    "type": "status_update",
                    "data": status,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
            await asyncio.sleep(1)  # Update every second


manager = ConnectionManager()


# Pydantic models for API
class StartAgentRequest(BaseModel):
    task: str
    planner_model: str = "qwen2.5:3b"
    coder_model: str = "qwen2.5-coder:7b"
    max_iterations: int = 50
    goal_timeout: int = 300
    project_id: Optional[str] = None


class GoalRequest(BaseModel):
    description: str
    priority: int = 5
    tags: List[str] = []


class MemoryQueryRequest(BaseModel):
    query: str
    category: Optional[str] = None
    top_k: int = 10


# Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/status")
async def get_status():
    if not manager.agent:
        return {"running": False, "message": "No agent running"}
    return manager.agent.get_status()


@app.post("/api/agent/start")
async def start_agent(request: StartAgentRequest):
    if manager.agent and manager.agent.running:
        raise HTTPException(status_code=400, detail="Agent already running")

    # Import here to avoid circular imports
    import config
    from agents.analyst import AnalystAgent
    from agents.architect import ArchitectAgent
    from agents.critic import CriticAgent
    from agents.planner import PlannerAgent
    from agents.consensus import ConsensusAgent
    from agents.polyglot_file_planner import PolyglotFilePlanner
    from agents.coder import CoderAgent
    from agents.fixer import FixerAgent
    from agents.import_validator import ImportValidatorAgent
    from agents.test_generator import TestGeneratorAgent

    # Create agents
    pm = request.planner_model
    cm = request.coder_model

    analyst = AnalystAgent(model=pm)
    architect = ArchitectAgent(model=pm)
    critic = CriticAgent(model=pm)
    planner = PlannerAgent(model=pm)
    consensus = ConsensusAgent(model=pm)
    polyglot_planner = PolyglotFilePlanner(model=pm)
    coder = CoderAgent(model=cm)
    fixer = FixerAgent(model=cm)
    import_validator = ImportValidatorAgent(model=cm)
    test_generator = TestGeneratorAgent(model=cm)

    # Create autonomous agent
    project_dir = config.PROJECT_DIR
    agent = AutonomousAgent(
        project_dir=project_dir,
        project_id=request.project_id,
        max_iterations=request.max_iterations,
        goal_timeout=request.goal_timeout,
    )

    # Register agents
    agent.register_agent("analyst", analyst)
    agent.register_agent("architect", architect)
    agent.register_agent("critic", critic)
    agent.register_agent("planner", planner)
    agent.register_agent("consensus", consensus)
    agent.register_agent("file_planner", polyglot_planner)
    agent.register_agent("coder", coder)
    agent.register_agent("fixer", fixer)
    agent.register_agent("import_validator", import_validator)
    agent.register_agent("test_generator", test_generator)

    # Add initial goal
    agent.add_goal(request.task, priority=10, tags=["initial", "user"])

    # Set up callbacks for real-time updates
    def on_goal_complete(goal):
        asyncio.create_task(manager.broadcast({
            "type": "goal_complete",
            "data": {"id": goal.id, "description": goal.description, "status": goal.status.value},
            "timestamp": datetime.now().isoformat()
        }))

    def on_task_complete(task):
        asyncio.create_task(manager.broadcast({
            "type": "task_complete",
            "data": {"id": task.id, "description": task.description, "agent_type": task.agent_type},
            "timestamp": datetime.now().isoformat()
        }))

    def on_error(task, error):
        asyncio.create_task(manager.broadcast({
            "type": "task_error",
            "data": {"id": task.id, "description": task.description, "error": str(error)},
            "timestamp": datetime.now().isoformat()
        }))

    agent.on_goal_complete = on_goal_complete
    agent.on_task_complete = on_task_complete
    agent.on_error = on_error

    manager.set_agent(agent)

    # Run agent in background
    asyncio.create_task(run_agent_background(agent))

    return {"status": "started", "project_id": agent.project_id}


async def run_agent_background(agent: AutonomousAgent):
    """Run the autonomous agent in background"""
    try:
        summary = agent.run()
        await manager.broadcast({
            "type": "agent_finished",
            "data": summary,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.exception("Agent error")
        await manager.broadcast({
            "type": "agent_error",
            "data": {"error": str(e)},
            "timestamp": datetime.now().isoformat()
        })
    finally:
        manager.agent = None


@app.post("/api/agent/stop")
async def stop_agent():
    if manager.agent:
        manager.agent.stop()
        return {"status": "stopping"}
    raise HTTPException(status_code=400, detail="No agent running")


@app.post("/api/agent/goal")
async def add_goal(request: GoalRequest):
    if not manager.agent:
        raise HTTPException(status_code=400, detail="No agent running")
    goal_id = manager.agent.add_goal(request.description, request.priority, request.tags)
    return {"goal_id": goal_id}


@app.get("/api/agent/goals")
async def list_goals():
    if not manager.agent:
        return {"goals": []}
    return {
        "goals": [
            {
                "id": g.id,
                "description": g.description,
                "status": g.status.value,
                "priority": g.priority,
                "tags": g.tags,
                "created_at": g.created_at,
                "subtasks": g.subtasks
            }
            for g in manager.agent.goals.values()
        ]
    }


@app.get("/api/agent/tasks")
async def list_tasks():
    if not manager.agent:
        return {"tasks": []}
    return {
        "tasks": [
            {
                "id": t.id,
                "goal_id": t.goal_id,
                "description": t.description,
                "agent_type": t.agent_type,
                "status": t.status.value,
                "attempts": t.attempts,
                "result": t.result[:500] if t.result else None,
                "error": t.error
            }
            for t in manager.agent.tasks.values()
        ]
    }


@app.get("/api/project/files")
async def list_project_files():
    """List generated project files"""
    project_dir = config.PROJECT_DIR
    if not project_dir.exists():
        return {"files": []}

    files = []
    for f in project_dir.rglob("*"):
        if f.is_file():
            rel = f.relative_to(project_dir)
            files.append({
                "path": str(rel),
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })
    return {"files": files}


@app.get("/api/project/file/{path:path}")
async def get_file(path: str):
    """Get file content"""
    project_dir = config.PROJECT_DIR
    file_path = project_dir / path
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # Prevent directory traversal
    try:
        file_path.relative_to(project_dir)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    content = file_path.read_text(encoding="utf-8", errors="replace")
    return {"path": path, "content": content}


# Memory endpoints
@app.get("/api/memory/stats")
async def memory_stats(project_id: str = "default"):
    store = get_memory_store(project_id)
    return store.stats()


@app.post("/api/memory/search")
async def memory_search(request: MemoryQueryRequest):
    from utils.memory import recall_relevant
    result = recall_relevant(request.query, max_entries=request.top_k)
    return {"results": result}


@app.get("/api/memory/entries")
async def memory_entries(project_id: str = "default", category: str = None, limit: int = 50):
    store = get_memory_store(project_id)
    entries = store.get_recent(category, limit) if category else store.get_recent(limit=limit)
    return {"entries": [e.to_dict() for e in entries]}


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial status if agent is running
        if manager.agent:
            status = manager.agent.get_status()
            await websocket.send_json({
                "type": "status_update",
                "data": status,
                "timestamp": datetime.now().isoformat()
            })

        while True:
            # Keep connection alive, handle incoming messages if needed
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)