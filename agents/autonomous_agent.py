"""
agents/autonomous_agent.py
Autonomous software engineering agent for continuous operation.
"""

import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

import config
from agents.base_agent import BaseAgent
from utils.memory import get_memory_store, recall_relevant, remember_decision, remember_error_fix, remember_code_pattern
from utils.language import detect_language, get_language_config, get_language_agent_prompt

logger = logging.getLogger(__name__)


class GoalStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class Goal:
    """A high-level goal for the autonomous agent."""
    id: str
    description: str
    status: GoalStatus = GoalStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    subtasks: List[str] = field(default_factory=list)
    result: Optional[str] = None
    error: Optional[str] = None
    priority: int = 5  # 1-10, higher = more important
    tags: List[str] = field(default_factory=list)


@dataclass
class Task:
    """A concrete task to execute."""
    id: str
    goal_id: str
    description: str
    agent_type: str  # Which agent should handle this
    status: GoalStatus = GoalStatus.PENDING
    created_at: float = field(default_factory=time.time)
    result: Optional[str] = None
    error: Optional[str] = None
    attempts: int = 0
    max_attempts: int = 3


class AutonomousAgent:
    """
    Autonomous agent that continuously works on goals.
    Manages goal decomposition, task execution, and self-improvement.
    """

    def __init__(
        self,
        project_dir: Path,
        project_id: str = None,
        max_iterations: int = None,
        goal_timeout: int = None,
    ):
        self.project_dir = project_dir
        self.project_id = project_id or f"auto_{int(time.time())}"
        self.max_iterations = max_iterations or config.AUTONOMOUS_MAX_ITERATIONS
        self.goal_timeout = goal_timeout or config.AUTONOMOUS_GOAL_TIMEOUT

        self.goals: Dict[str, Goal] = {}
        self.tasks: Dict[str, Task] = {}
        self.iteration = 0
        self.idle_cycles = 0
        self.running = False

        # Memory
        self.memory = get_memory_store(self.project_id)

        # Language detection
        self.language = detect_language(project_dir)
        self.lang_config = get_language_config(self.language)

        # Agent registry (to be populated)
        self.agents: Dict[str, BaseAgent] = {}

        # Callbacks
        self.on_goal_complete: Optional[Callable] = None
        self.on_task_complete: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

        logger.info("AutonomousAgent initialized for project %s (language: %s)",
                   self.project_id, self.language)

    def register_agent(self, name: str, agent: BaseAgent):
        """Register an agent for task execution."""
        self.agents[name] = agent
        logger.debug("Registered agent: %s", name)

    def add_goal(self, description: str, priority: int = 5, tags: List[str] = None) -> str:
        """Add a new high-level goal."""
        goal_id = f"goal_{len(self.goals) + 1}_{int(time.time())}"
        goal = Goal(
            id=goal_id,
            description=description,
            priority=priority,
            tags=tags or [],
        )
        self.goals[goal_id] = goal
        logger.info("Added goal: %s - %s", goal_id, description)
        return goal_id

    def decompose_goal(self, goal: Goal) -> List[Task]:
        """Decompose a goal into executable tasks using the planner agent."""
        if "planner" not in self.agents:
            logger.warning("No planner agent registered, cannot decompose goal")
            return []

        # Get relevant memory context
        context = recall_relevant(self.project_id, goal.description)

        prompt = f"""
Goal: {goal.description}

Project Context:
- Language: {self.language}
- Project Directory: {self.project_dir}
- Relevant Memory:
{context}

Decompose this goal into specific, executable tasks. Each task should specify:
1. A clear description
2. Which agent type should handle it (analyst, architect, coder, tester, etc.)
3. Expected output

Return as JSON array of tasks.
"""
        try:
            response = self.agents["planner"].run(prompt, use_cache=False)
            # Parse tasks from response
            tasks = self._parse_tasks(response, goal.id)
            goal.subtasks = [t.id for t in tasks]
            for task in tasks:
                self.tasks[task.id] = task
            logger.info("Decomposed goal %s into %d tasks", goal.id, len(tasks))
            return tasks
        except Exception as e:
            logger.error("Failed to decompose goal %s: %s", goal.id, e)
            return []

    def _parse_tasks(self, response: str, goal_id: str) -> List[Task]:
        """Parse task list from planner response."""
        import json
        from utils.json_parser import parse_json

        tasks = []
        try:
            parsed = parse_json(response)
            task_list = parsed.get("tasks", parsed) if isinstance(parsed, dict) else parsed

            if isinstance(task_list, list):
                for i, task_data in enumerate(task_list):
                    if isinstance(task_data, dict):
                        task = Task(
                            id=f"{goal_id}_task_{i}",
                            goal_id=goal_id,
                            description=task_data.get("description", ""),
                            agent_type=task_data.get("agent_type", "coder"),
                            max_attempts=task_data.get("max_attempts", 3),
                        )
                        tasks.append(task)
        except Exception as e:
            logger.warning("Failed to parse tasks from response: %s", e)
            # Fallback: create a single generic task
            tasks.append(Task(
                id=f"{goal_id}_task_0",
                goal_id=goal_id,
                description=response[:500],
                agent_type="coder",
            ))

        return tasks

    def get_next_task(self) -> Optional[Task]:
        """Get the next pending task, prioritized by goal priority."""
        # Find highest priority goal with pending tasks
        pending_goals = [
            g for g in self.goals.values()
            if g.status in (GoalStatus.PENDING, GoalStatus.IN_PROGRESS)
        ]
        if not pending_goals:
            return None

        pending_goals.sort(key=lambda g: g.priority, reverse=True)

        for goal in pending_goals:
            for task_id in goal.subtasks:
                task = self.tasks.get(task_id)
                if task and task.status == GoalStatus.PENDING:
                    return task

        return None

    def execute_task(self, task: Task) -> bool:
        """Execute a single task using the appropriate agent."""
        agent = self.agents.get(task.agent_type)
        if not agent:
            logger.error("No agent registered for type: %s", task.agent_type)
            task.status = GoalStatus.FAILED
            task.error = f"No agent for type: {task.agent_type}"
            return False

        task.status = GoalStatus.IN_PROGRESS
        task.attempts += 1

        # Get relevant memory for this task
        context = recall_relevant(self.project_id, task.description)

        # Build prompt with language-specific guidance
        lang_prompt = get_language_agent_prompt(self.language)
        prompt = f"""
{lang_prompt}

Task: {task.description}

Project Language: {self.language}
Project Directory: {self.project_dir}

Relevant Project Memory:
{context}

Execute this task and return the result.
"""

        try:
            logger.info("Executing task %s with agent %s", task.id, task.agent_type)
            result = agent.run(prompt, use_cache=False)

            task.result = result
            task.status = GoalStatus.COMPLETED

            # Remember successful pattern
            if task.agent_type == "coder":
                remember_code_pattern(
                    self.project_id,
                    result[:2000],
                    self.language,
                    task.description
                )

            if self.on_task_complete:
                self.on_task_complete(task)

            logger.info("Task %s completed successfully", task.id)
            return True

        except Exception as e:
            task.error = str(e)
            logger.error("Task %s failed: %s", task.id, e)

            if task.attempts >= task.max_attempts:
                task.status = GoalStatus.FAILED
                # Remember error fix for future
                remember_error_fix(
                    self.project_id,
                    str(e),
                    f"Task: {task.description}",
                    task.id
                )
            else:
                task.status = GoalStatus.PENDING  # Retry

            if self.on_error:
                self.on_error(task, e)

            return False

    def check_goal_completion(self, goal: Goal) -> bool:
        """Check if all subtasks of a goal are complete."""
        if not goal.subtasks:
            return False

        all_complete = all(
            self.tasks.get(tid, Task(id=tid, goal_id=goal.id, description="", agent_type="")).status == GoalStatus.COMPLETED
            for tid in goal.subtasks
        )

        if all_complete:
            goal.status = GoalStatus.COMPLETED
            goal.completed_at = time.time()
            if self.on_goal_complete:
                self.on_goal_complete(goal)
            logger.info("Goal %s completed", goal.id)
            return True

        # Check if any task failed permanently
        any_failed = any(
            self.tasks.get(tid, Task(id=tid, goal_id=goal.id, description="", agent_type="")).status == GoalStatus.FAILED
            for tid in goal.subtasks
        )

        if any_failed:
            goal.status = GoalStatus.FAILED
            logger.warning("Goal %s failed due to failed subtask", goal.id)

        return False

    def propose_new_goals(self) -> List[str]:
        """Propose new goals based on project state and memory."""
        if "analyst" not in self.agents:
            return []

        # Get project summary
        project_files = list(self.project_dir.rglob("*")) if self.project_dir.exists() else []
        py_files = [f for f in project_files if f.suffix == ".py"]

        prompt = f"""
Analyze the current project state and propose 1-3 new goals for continued development.

Project: {self.project_dir}
Language: {self.language}
Files: {len(py_files)} Python files
Recent goals: {[g.description for g in list(self.goals.values())[-5:]]}

Consider:
- Missing tests
- Incomplete features
- Technical debt
- Documentation gaps
- Performance improvements

Return JSON with "goals" array of {{"description": "...", "priority": 1-10, "tags": [...]}}.
"""
        try:
            response = self.agents["analyst"].run(prompt, use_cache=False)
            from utils.json_parser import parse_json
            parsed = parse_json(response)
            new_goal_ids = []
            for goal_data in parsed.get("goals", []):
                goal_id = self.add_goal(
                    goal_data.get("description", ""),
                    goal_data.get("priority", 5),
                    goal_data.get("tags", [])
                )
                new_goal_ids.append(goal_id)
            return new_goal_ids
        except Exception as e:
            logger.warning("Failed to propose new goals: %s", e)
            return []

    def run_iteration(self) -> bool:
        """Run one iteration of the autonomous loop."""
        self.iteration += 1
        logger.info("=== Autonomous Iteration %d ===", self.iteration)

        # Check for timed-out goals
        now = time.time()
        for goal in self.goals.values():
            if goal.status == GoalStatus.IN_PROGRESS and goal.started_at:
                if now - goal.started_at > self.goal_timeout:
                    goal.status = GoalStatus.FAILED
                    goal.error = "Timeout"
                    logger.warning("Goal %s timed out", goal.id)

        # Decompose any pending goals
        for goal in self.goals.values():
            if goal.status == GoalStatus.PENDING and not goal.subtasks:
                goal.status = GoalStatus.IN_PROGRESS
                goal.started_at = time.time()
                self.decompose_goal(goal)

        # Execute next task
        task = self.get_next_task()
        if task:
            self.execute_task(task)
            self.idle_cycles = 0
        else:
            self.idle_cycles += 1
            logger.debug("No pending tasks (idle cycles: %d)", self.idle_cycles)

        # Check goal completions
        for goal in self.goals.values():
            if goal.status == GoalStatus.IN_PROGRESS:
                self.check_goal_completion(goal)

        # Propose new goals if idle
        if self.idle_cycles >= config.AUTONOMOUS_IDLE_THRESHOLD:
            new_goals = self.propose_new_goals()
            if new_goals:
                logger.info("Proposed %d new goals after idle period", len(new_goals))
                self.idle_cycles = 0

        # Check if done
        active_goals = [g for g in self.goals.values() if g.status in (GoalStatus.PENDING, GoalStatus.IN_PROGRESS)]
        if not active_goals:
            logger.info("All goals completed")
            return False

        if self.iteration >= self.max_iterations:
            logger.warning("Max iterations reached")
            return False

        return True

    def run(self) -> Dict[str, Any]:
        """Run the autonomous loop until completion or max iterations."""
        self.running = True
        logger.info("Starting autonomous agent for project %s", self.project_id)

        try:
            while self.running and self.run_iteration():
                time.sleep(1)  # Brief pause between iterations

        except KeyboardInterrupt:
            logger.info("Autonomous agent interrupted")
        except Exception as e:
            logger.exception("Autonomous agent error: %s", e)
        finally:
            self.running = False

        # Return summary
        return {
            "project_id": self.project_id,
            "iterations": self.iteration,
            "goals_total": len(self.goals),
            "goals_completed": len([g for g in self.goals.values() if g.status == GoalStatus.COMPLETED]),
            "goals_failed": len([g for g in self.goals.values() if g.status == GoalStatus.FAILED]),
            "tasks_total": len(self.tasks),
            "tasks_completed": len([t for t in self.tasks.values() if t.status == GoalStatus.COMPLETED]),
            "tasks_failed": len([t for t in self.tasks.values() if t.status == GoalStatus.FAILED]),
        }

    def stop(self):
        """Stop the autonomous agent."""
        self.running = False
        logger.info("Autonomous agent stop requested")

    def get_status(self) -> Dict[str, Any]:
        """Get current status."""
        return {
            "project_id": self.project_id,
            "language": self.language,
            "iteration": self.iteration,
            "idle_cycles": self.idle_cycles,
            "running": self.running,
            "goals": {gid: {"description": g.description, "status": g.status.value, "priority": g.priority}
                      for gid, g in self.goals.items()},
            "tasks_pending": len([t for t in self.tasks.values() if t.status == GoalStatus.PENDING]),
            "tasks_in_progress": len([t for t in self.tasks.values() if t.status == GoalStatus.IN_PROGRESS]),
            "tasks_completed": len([t for t in self.tasks.values() if t.status == GoalStatus.COMPLETED]),
            "tasks_failed": len([t for t in self.tasks.values() if t.status == GoalStatus.FAILED]),
            "memory_stats": self.memory.stats(),
        }