from agents.base_agent import BaseAgent


class AnalystAgent(BaseAgent):

    def __init__(self):

        super().__init__(
            name="Analyst",
            system_prompt = """
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
num_predict=500
        )
