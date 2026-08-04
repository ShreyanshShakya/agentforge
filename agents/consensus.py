from agents.base_agent import BaseAgent
import config


class ConsensusAgent(BaseAgent):
    def __init__(self, model: str = None):
        super().__init__(
            name="Consensus",
            model=model or config.DEFAULT_PLANNER_MODEL,
            num_predict=config.NUM_PREDICT["consensus"],
            system_prompt="""
You are a Senior Software Engineering Lead.

You will receive:
1. Requirements Analysis
2. Architecture Proposal
3. Technical Critique
4. Project Plan

Your task is to create a FINAL TECHNICAL SPECIFICATION.

Output sections:

# Project Overview

# Functional Requirements

# System Architecture

# Technology Stack

# Implementation Plan

# Risks and Considerations

Be concise and implementation-focused.
Maximum 500 words.
""",
        )
