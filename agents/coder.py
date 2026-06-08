from agents.base_agent import BaseAgent


class CoderAgent(BaseAgent):

    def __init__(self):

        super().__init__(
            name="Coder",
            model="qwen2.5-coder:7b",
            system_prompt="""
You are a senior software engineer.

Generate project files using EXACTLY this format:

FILE: requirements.txt
<content>

END_FILE

FILE: README.md
<content>

END_FILE

FILE: main.py
<content>

END_FILE

FILE: config.py
<content>

END_FILE

Rules:
1. Do NOT use markdown code blocks.
2. Do NOT use ``` fences.
3. Every file MUST start with FILE:
4. Every file MUST end with END_FILE.
5. Output complete file contents.
""",
num_predict=4000
        )
