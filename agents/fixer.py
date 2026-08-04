from agents.base_agent import BaseAgent
import config


class FixerAgent(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            name="Fixer",
            model=model or config.DEFAULT_CODER_MODEL,
            num_predict=config.NUM_PREDICT["fixer"],
            system_prompt="""
You are a senior Python engineer.

You will receive:
1. ERROR TYPE
2. PROJECT STRUCTURE
3. CURRENT FILE
4. FILE DESCRIPTION
5. ERROR LOG
6. REPAIR HISTORY
7. CURRENT CODE

Fix the code to resolve the error. If there is a REPAIR HISTORY, ensure you try a different approach than your previous failed attempts.

Return ONLY the corrected code.

Do not explain.
Do not use markdown.
""",
        )
