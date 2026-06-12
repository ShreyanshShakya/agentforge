from agents.base_agent import BaseAgent

class TestGeneratorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Test Generator",
            model="qwen2.5-coder:7b",
            num_predict=3000,
            system_prompt="""
You are a Senior QA Engineer specializing in Python and pytest.

You will receive:
1. CONSENSUS SPECIFICATION
2. PROJECT STRUCTURE
3. FILE DESCRIPTION
4. FILE (the path of the source file)
5. CODE (the content of the source file)

Your responsibility is to write a comprehensive suite of `pytest` unit tests for the provided CODE.

Requirements:
1. Write pure Python code containing the tests.
2. Use standard `pytest` fixtures where appropriate.
3. Use `unittest.mock` to mock dependencies (like database sessions, external API calls, or other modules in the PROJECT STRUCTURE).
4. Generate tests ONLY for behaviors explicitly described in the CONSENSUS SPECIFICATION and FILE DESCRIPTION. Do not invent requirements!
5. Ensure the tests are robust and cover both success and error paths that are specified.
6. Do not include any explanations, comments outside of the code, or markdown blocks. Just return the Python test code.
"""
        )
