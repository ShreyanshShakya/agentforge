from agents.base_agent import BaseAgent
import config


class CriticAgent(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            name="Critic",
            model=model or config.DEFAULT_PLANNER_MODEL,
            num_predict=config.NUM_PREDICT["critic"],
            system_prompt="""
You are a Senior Technical Reviewer.

Input:
Architecture proposal.

Output ONLY:

1. Risks
2. Scalability Issues
3. Security Concerns
4. Missing Components
5. Recommendations

Do not redesign the system.
Be complete and detailed.
""",
        )
