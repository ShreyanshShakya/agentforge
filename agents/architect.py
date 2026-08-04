from agents.base_agent import BaseAgent
import config


class ArchitectAgent(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            name="Architect",
            model=model or config.DEFAULT_PLANNER_MODEL,
            num_predict=config.NUM_PREDICT["architect"],
            system_prompt="""
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
        )
