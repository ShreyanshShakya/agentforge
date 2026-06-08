from agents.analyst import AnalystAgent
from agents.planner import PlannerAgent
from agents.consensus import ConsensusAgent
from agents.critic import CriticAgent
from agents.architect import ArchitectAgent
from agents.coder import CoderAgent
from agents.file_planner import FilePlannerAgent
from utils.json_parser import parse_json
from agents.validator import ValidatorAgent
from agents.fixer import FixerAgent
from utils.compiler import check_python_file
import os
import re

task = """
Build a FastAPI Todo API.
"""


# Create agent instances
analyst = AnalystAgent()
architect = ArchitectAgent()
critic = CriticAgent()
planner = PlannerAgent()
consensus = ConsensusAgent()
coder = CoderAgent()
file_planner = FilePlannerAgent()
validator = ValidatorAgent()
fixer = FixerAgent()

# Run workflow
analysis = analyst.run(task)

architecture = architect.run(
    f"""
    Requirements:
    {analysis}
    """
)

critique = critic.run(
    f"""
    Requirements:
    {analysis}

    Architecture:
    {architecture}
    """
)

plan = planner.run(
    f"""
    Requirements:
    {analysis}

    Architecture:
    {architecture}

    Critique:
    {critique}
    """
)

consensus_output = consensus.run(
    f"""
ANALYSIS:
{analysis}

ARCHITECTURE:
{architecture}

CRITIQUE:
{critique}

PLAN:
{plan}
"""
)


# Print results
print("\n===== ANALYST =====\n")
print(analysis)

print("\n===== ARCHITECT =====\n")
print(architecture)

print("\n===== CRITIC =====\n")
print(critique)

print("\n===== PLANNER =====\n")
print(plan)

print("\n===== CONSENSUS =====\n")
print(consensus_output)

with open(
    "output/specification.md",
    "w",
    encoding="utf-8"
) as f:
    f.write(consensus_output)
print(
    "\nSpecification saved to output/specification.md"
)


file_plan = file_planner.run(
    consensus_output
)

with open(
    "output/file_plan.json",
    "w",
    encoding="utf-8"
) as f:
    f.write(file_plan)

parsed_file_plan = parse_json(
    file_plan
)

print("\n===== FILE PLAN =====\n")
print(parsed_file_plan)

project_structure = "\n".join(
    [
        file["path"]
        for file in parsed_file_plan["files"]
    ]
)

for file_info in parsed_file_plan["files"]:

    path = file_info["path"]

    description = file_info["description"]

    print(
        f"""
Generating:
{path}

Known Project Structure:
{project_structure}
"""
    )

    code = coder.run(
        f"""
PROJECT SPECIFICATION

{consensus_output}

PROJECT STRUCTURE

{project_structure}

CURRENT FILE

{path}

FILE DESCRIPTION

{description}

IMPORTANT:

Only generate code for:
{path}

The generated code must be compatible with
all files listed in PROJECT STRUCTURE.

Use imports that match the structure.

Do not generate code for any other file.

Do not use markdown.

Return only file content.
"""
    )

    code = re.sub(
        r"FILE:.*?\n",
        "",
        code
    )

    code = code.replace(
        "END_FILE",
        ""
    )

    code = re.sub(r"```[a-zA-Z]*\n?", "", code)
    code = re.sub(r"```\n?", "", code)
    code = code.strip()

    validated_code = validator.run(
    f"""
FILE PATH:
{path}

DESCRIPTION:
{description}

GENERATED CODE:

{code}
"""
    )

    full_path = os.path.join(
        "output/project",
        path
    )

    os.makedirs(
        os.path.dirname(full_path),
        exist_ok=True
    )

    with open(
        full_path,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(validated_code)

    if path.endswith(".py"):

        is_valid, error = check_python_file(
            full_path
        )

    else:

        is_valid = True
        error = None


    if not is_valid:
        MAX_RETRIES = 3

        for attempt in range(MAX_RETRIES):
            is_valid, error = check_python_file(full_path)

            if is_valid:
                print(f"✓ Passed: {path}")
                break

            print(f"Fix attempt {attempt + 1} for {path}")

            safe_name = path.replace("/", "_").replace("\\", "_")
            os.makedirs("output/errors", exist_ok=True)
            with open(f"output/errors/{safe_name}.txt", "w", encoding="utf-8") as f:
                f.write(error)

            validated_code = fixer.run(
                f"""
PROJECT STRUCTURE

{project_structure}

CURRENT FILE

{path}

FILE DESCRIPTION

{description}

COMPILATION ERROR

{error}

CURRENT CODE

{validated_code}

Fix the file.

Ensure imports match the project structure.

Return only corrected file content.
"""
            )

            validated_code = re.sub(r"```[a-zA-Z]*\n?", "", validated_code)
            validated_code = re.sub(r"```\n?", "", validated_code)
            validated_code = validated_code.strip()

            with open(full_path, "w", encoding="utf-8") as f:
                f.write(validated_code)

        is_valid, error = check_python_file(full_path)
        if is_valid:
            print(f"✓ Passed successfully after fixes: {path}")
        else:
            print(f" Still failing after {MAX_RETRIES} attempts: {path}")

    print(
        f"Created: {full_path}"
    )

