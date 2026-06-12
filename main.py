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
from agents.import_validator import ImportValidatorAgent
from agents.test_generator import TestGeneratorAgent
import os
import re
import subprocess

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
fixer = FixerAgent()
import_validator = ImportValidatorAgent()
test_generator = TestGeneratorAgent()

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

def run_test_pipeline(path, validated_code, context_structure, full_path, consensus_output, description):
    if path.endswith("__init__.py") or path.endswith(".txt"):
        return True, None, None

    import_errors = import_validator.run(
        f"PROJECT STRUCTURE\n\n{context_structure}\n\nFILE\n\n{path}\n\nCODE\n\n{validated_code}"
    )
    if "VALID" not in import_errors:
        return False, f"Import Validation Failed:\n{import_errors}", "IMPORT_ERROR"
    
    test_file_path = full_path.replace("output/project/", "output/project/tests/")
    test_dir = os.path.dirname(test_file_path)
    os.makedirs(test_dir, exist_ok=True)
    basename = os.path.basename(test_file_path)
    if not basename.startswith("test_"):
        test_file_path = os.path.join(test_dir, "test_" + basename)
    
    if not os.path.exists(test_file_path):
        test_code = test_generator.run(f"CONSENSUS SPECIFICATION\n\n{consensus_output}\n\nPROJECT STRUCTURE\n\n{context_structure}\n\nFILE DESCRIPTION\n\n{description}\n\nFILE\n\n{path}\n\nCODE\n\n{validated_code}")
        test_code = re.sub(r"```[a-zA-Z]*\n?", "", test_code)
        test_code = re.sub(r"```\n?", "", test_code).strip()
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write(test_code)
        
    result = subprocess.run(["python", "-m", "pytest", test_file_path], capture_output=True, text=True, cwd="output/project")
    if result.returncode != 0:
        return False, f"Pytest Execution Failed:\n{result.stderr}\n{result.stdout}", "PYTEST_FAILURE"
    return True, None, None

for file_info in parsed_file_plan["files"]:

    path = file_info["path"]
    description = file_info["description"]

    depends_on = file_info.get("depends_on", [])
    context_structure = "\n".join([path] + depends_on)

    print(
        f"""
Generating:
{path}

Known Project Structure:
{context_structure}
"""
    )

    code = coder.run(
        f"""
PROJECT SPECIFICATION

{consensus_output}

PROJECT STRUCTURE

{context_structure}

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

    validated_code = code

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

    repair_history = []
    error_type = None

    if path.endswith(".py"):
        is_valid, error = check_python_file(full_path)
        if not is_valid:
            error_type = "COMPILATION_ERROR"
        else:
            is_valid, error, error_type = run_test_pipeline(path, validated_code, context_structure, full_path, consensus_output, description)

    else:

        is_valid = True
        error = None
        error_type = None


    if not is_valid:
        MAX_RETRIES = 3

        for attempt in range(MAX_RETRIES):
            formatted_repair_history = "\\n---\\n".join(repair_history)
            
            validated_code = fixer.run(
                f"""
ERROR TYPE:
{error_type}

PROJECT STRUCTURE:
{context_structure}

CURRENT FILE:
{path}

FILE DESCRIPTION:
{description}

ERROR LOG:
{error}

REPAIR HISTORY:
{formatted_repair_history}

CURRENT CODE:
{validated_code}
"""
            )

            validated_code = re.sub(r"```[a-zA-Z]*\n?", "", validated_code)
            validated_code = re.sub(r"```\n?", "", validated_code)
            validated_code = validated_code.strip()

            with open(full_path, "w", encoding="utf-8") as f:
                f.write(validated_code)

            repair_history.append(f"[{error_type}]\\n{error}")

            is_valid, error = check_python_file(full_path)

            if not is_valid:
                error_type = "COMPILATION_ERROR"
            else:
                is_valid, error, error_type = run_test_pipeline(path, validated_code, context_structure, full_path, consensus_output, description)
            
            if is_valid:
                print(f"✓ Passed: {path}")
                break

            print(f"Fix attempt {attempt + 1} for {path}")

            safe_name = path.replace("/", "_").replace("\\", "_")
            os.makedirs("output/errors", exist_ok=True)
            with open(f"output/errors/{safe_name}.txt", "w", encoding="utf-8") as f:
                f.write(error)

        is_valid, error = check_python_file(full_path)
        if is_valid:
            print(f"✓ Passed successfully after fixes: {path}")
        else:
            print(f" Still failing after {MAX_RETRIES} attempts: {path}")



    print(
        f"Created: {full_path}"
    )

