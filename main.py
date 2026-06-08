from agents.analyst import AnalystAgent
from agents.planner import PlannerAgent
from agents.consensus import ConsensusAgent
from agents.critic import CriticAgent
from agents.architect import ArchitectAgent
from agents.coder import CoderAgent
from agents.file_planner import FilePlannerAgent
from utils.json_parser import parse_json
from agents.validator import ValidatorAgent
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

for file_info in parsed_file_plan["files"]:

    path = file_info["path"]

    description = file_info["description"]

    print(f"\nGenerating {path}")

    code = coder.run(
        f"""
PROJECT SPECIFICATION

{consensus_output}

FILE TO GENERATE

{path}

DESCRIPTION

{description}

Generate ONLY the content of this file.

Do not include markdown.
Do not include code fences.
Do not include explanations.
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

    print(
        f"Created: {full_path}"
    )

