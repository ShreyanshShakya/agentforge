from agents.base_agent import BaseAgent
import config


class AnalystAgent(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            name="Analyst",
            model=model or config.DEFAULT_PLANNER_MODEL,
            num_predict=config.NUM_PREDICT["analyst"],
            system_prompt="""
You are a Requirements Analyst.

Output ONLY:

1. Objectives
2. Functional Requirements
3. Non-Functional Requirements
4. Constraints

Do not discuss architecture.
Do not create implementation plans.
Be complete and detailed.
""",
        )
