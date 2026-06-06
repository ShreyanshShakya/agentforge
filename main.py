from agents.analyst import AnalystAgent
from agents.planner import PlannerAgent
from agents.critic import CriticAgent
from agents.architect import ArchitectAgent


task = """
Build a travel demand intelligence system
"""


# Create agent instances
analyst = AnalystAgent()
architect = ArchitectAgent()
critic = CriticAgent()
planner = PlannerAgent()


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


# Print results
print("\n===== ANALYST =====\n")
print(analysis)

print("\n===== ARCHITECT =====\n")
print(architecture)

print("\n===== CRITIC =====\n")
print(critique)

print("\n===== PLANNER =====\n")
print(plan)
