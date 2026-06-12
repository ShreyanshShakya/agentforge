from agents.base_agent import BaseAgent

class ExecutionAgent(BaseAgent):

    def __init__(self):

        super().__init__(
            name="Execution Agent",
            model="qwen2.5-coder:7b",
            num_predict=2500,
            system_prompt="""
You are a software testing engineer.

You will receive:

1. Project structure
2. File content
3. Runtime error

Fix runtime issues.

Return only corrected code.
"""
        )
