from agents.base_agent import BaseAgent
import config


class FilePlannerAgent(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            name="File Planner",
            model=model or config.DEFAULT_PLANNER_MODEL,
            num_predict=config.NUM_PREDICT["file_planner"],
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
""",
        )
