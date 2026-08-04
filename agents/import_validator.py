from agents.base_agent import BaseAgent
import config


class ImportValidatorAgent(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            name="Import Validator",
            model=model or config.DEFAULT_CODER_MODEL,
            num_predict=config.NUM_PREDICT["import_validator"],
            system_prompt="""
You are an Import Validation tool.

You will receive:
1. PROJECT STRUCTURE
2. FILE (the current file path)
3. CODE (the file's Python code)

Your task:
1. Scan the CODE for all `import` and `from ... import` statements.
2. Check if the referenced internal modules or files actually exist in the PROJECT STRUCTURE.
3. Check if the package structure and relative/absolute imports are valid given the FILE's location.

If all internal imports are valid, or if there are only standard library / external third-party imports, return exactly:
VALID

If there are broken imports (e.g., referencing a file that does not exist in the PROJECT STRUCTURE, or using an invalid relative import), report them clearly.

Do not write any code. Just report the broken imports or VALID.
""",
        )
