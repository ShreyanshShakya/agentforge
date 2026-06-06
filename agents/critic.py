from agents.base_agent import BaseAgent


class CriticAgent(BaseAgent):

    def __init__(self):

        super().__init__(
            name="Critic",
            system_prompt = """
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
Maximum 200 words.
"""
        )
