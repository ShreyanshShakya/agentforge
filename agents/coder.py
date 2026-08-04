from agents.base_agent import BaseAgent
import config


class CoderAgent(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            name="Coder",
            model=model or config.DEFAULT_CODER_MODEL,
            num_predict=config.NUM_PREDICT["coder"],
            system_prompt="""
You are a senior software engineer.

Generate project files using EXACTLY this format:

FILE: requirements.txt
<content>

END_FILE

FILE: README.md
<content>

END_FILE

Rules:
1. Do NOT use markdown code blocks.
2. Do NOT use ``` fences.
3. Every file MUST start with FILE:
4. Every file MUST end with END_FILE.
5. Output complete file contents.
""",
        )
