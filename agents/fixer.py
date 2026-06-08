from agents.base_agent import BaseAgent


class FixerAgent(BaseAgent):

    def __init__(self):

        super().__init__(
            name="Fixer",
            model="qwen2.5-coder:7b",
            num_predict=3000,
            system_prompt="""
You are a senior Python engineer.

You will receive:

1. File path
2. File content
3. Compilation error

Fix the code.

Return ONLY corrected code.

Do not explain.
Do not use markdown.
"""
        )
