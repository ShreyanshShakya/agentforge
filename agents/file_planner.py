from agents.base_agent import BaseAgent


class FilePlannerAgent(BaseAgent):

    def __init__(self):

        super().__init__(
            name="File Planner",
            model="qwen2.5:3b",
            num_predict=2000,
            system_prompt="""
You are a software architect.

Given a technical specification:

Generate a complete project file structure.

Output ONLY valid JSON.

Example:

{
  "project_name": "todo-api",
  "files": [
    {
      "path": "requirements.txt",
      "description": "Python dependencies"
    },
    {
      "path": "app/main.py",
      "description": "FastAPI application entrypoint",
      "depends_on": [
        "app/auth/routers/login.py",
        "app/todos/routers/v1/todos.py"
      ]
    }
  ]
}
"""
        )
