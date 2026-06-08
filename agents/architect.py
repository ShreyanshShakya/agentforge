from agents.base_agent import BaseAgent


class ArchitectAgent(BaseAgent):

    def __init__(self):

        super().__init__(
            name="Architect",
            system_prompt = """
You are a Software Architect.

Input:
Requirements document.

Output ONLY:

1. System Architecture
2. Major Components
3. Technology Stack
4. Data Flow

Do not rewrite requirements.
Do not create implementation tasks.
Be complete and detailed.
""",
num_predict=700
        )
