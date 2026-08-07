"""
AgentForge Utils Package
"""

from utils.cleaner import strip_markdown
from utils.compiler import check_python_file
from utils.json_parser import parse_json
from utils.file_writer import save_generated_project
from utils.executor import execute_python_file
from utils.language import (
    detect_language,
    get_language_config,
    get_validator_command,
    get_test_command,
    get_build_command,
    get_run_command,
    get_package_install_command,
    get_language_agent_prompt,
    get_file_template,
    LANGUAGE_CONFIGS,
)
from utils.memory import (
    MemoryStore,
    MemoryEntry,
    get_memory_store,
    remember_decision,
    remember_code_pattern,
    remember_error_fix,
    remember_architecture,
    remember_requirement,
    recall_relevant,
)

__all__ = [
    "strip_markdown",
    "check_python_file",
    "parse_json",
    "save_generated_project",
    "execute_python_file",
    "detect_language",
    "get_language_config",
    "get_validator_command",
    "get_test_command",
    "get_build_command",
    "get_run_command",
    "get_package_install_command",
    "get_language_agent_prompt",
    "get_file_template",
    "LANGUAGE_CONFIGS",
    "MemoryStore",
    "MemoryEntry",
    "get_memory_store",
    "remember_decision",
    "remember_code_pattern",
    "remember_error_fix",
    "remember_architecture",
    "remember_requirement",
    "recall_relevant",
]