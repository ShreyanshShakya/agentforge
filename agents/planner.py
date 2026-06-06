from agents.base_agent import BaseAgent


class PlannerAgent(BaseAgent):

    def __init__(self):

        super().__init__(
            name="Planner",
            system_prompt = """
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

Maximum 600 words.
"""
        )
