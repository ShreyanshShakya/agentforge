from agents.base_agent import BaseAgent
import config


class PlannerAgent(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            name="Planner",
            model=model or config.DEFAULT_PLANNER_MODEL,
            num_predict=config.NUM_PREDICT["planner"],
            system_prompt="""
You are a Technical Project Planner.

Input:
Requirements
Architecture
Critique

Output ONLY:

Phase 1:
Tasks

Phase 2:
Tasks

Phase 3:
Tasks

For each task provide:
- Description
- Dependencies
- Deliverables

Do not discuss architecture.
Do not discuss requirements.

Be complete and detailed.
""",
        )
