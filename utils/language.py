"""
utils/language.py
Multi-language support: detection, configuration, and language-specific utilities.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any

import config


class LanguageConfig:
    """Configuration for a specific programming language."""

    def __init__(self, name: str, cfg: Dict[str, Any]):
        self.name = name
        self.extensions: List[str] = cfg.get("extensions", [])
        self.test_pattern: str = cfg.get("test_pattern", "")
        self.test_framework: str = cfg.get("test_framework", "")
        self.build_cmd: Optional[str] = cfg.get("build_cmd")
        self.run_cmd: str = cfg.get("run_cmd", "")
        self.package_manager: str = cfg.get("package_manager", "")
        self.config_files: List[str] = cfg.get("config_files", [])
        self.validator: str = cfg.get("validator", "")

    def matches_extension(self, filepath: str) -> bool:
        return any(filepath.endswith(ext) for ext in self.extensions)

    def get_test_filename(self, source_path: str) -> str:
        base = Path(source_path).stem
        if self.name == "python":
            return f"test_{base}.py"
        elif self.name in ("javascript", "typescript"):
            return f"{base}.test.{self.extensions[0][1:]}"
        elif self.name == "go":
            return f"{base}_test.go"
        elif self.name == "rust":
            return f"{base}_test.rs"
        elif self.name == "java":
            return f"{base}Test.java"
        elif self.name == "csharp":
            return f"{base}Tests.cs"
        return f"test_{base}{self.extensions[0]}"


# Load language configs from config.py
LANGUAGE_CONFIGS: Dict[str, LanguageConfig] = {
    name: LanguageConfig(name, cfg) for name, cfg in config.SUPPORTED_LANGUAGES.items()
}


def detect_language(project_dir: Path, file_plan: List[Dict] = None) -> str:
    """
    Detect the primary language of a project.
    Priority: config files > file extensions in plan > file extensions on disk.
    """
    # Check for config files first (most reliable)
    for lang_name, lang_cfg in LANGUAGE_CONFIGS.items():
        for config_file in lang_cfg.config_files:
            matches = list(project_dir.rglob(config_file))
            if matches:
                return lang_name

    # Check file plan if provided
    if file_plan:
        ext_counts: Dict[str, int] = {}
        for fi in file_plan:
            path = fi.get("path", "")
            for lang_name, lang_cfg in LANGUAGE_CONFIGS.items():
                if lang_cfg.matches_extension(path):
                    ext_counts[lang_name] = ext_counts.get(lang_name, 0) + 1
        if ext_counts:
            return max(ext_counts, key=ext_counts.get)

    # Fallback: scan project directory
    ext_counts = {}
    for lang_name, lang_cfg in LANGUAGE_CONFIGS.items():
        for ext in lang_cfg.extensions:
            count = len(list(project_dir.rglob(f"*{ext}")))
            if count > 0:
                ext_counts[lang_name] = ext_counts.get(lang_name, 0) + count

    if ext_counts:
        return max(ext_counts, key=ext_counts.get)

    return config.DEFAULT_LANGUAGE


def get_language_config(language: str = None) -> LanguageConfig:
    """Get language configuration, defaulting to DEFAULT_LANGUAGE."""
    lang = language or config.DEFAULT_LANGUAGE
    return LANGUAGE_CONFIGS.get(lang, LANGUAGE_CONFIGS[config.DEFAULT_LANGUAGE])


def get_validator_command(language: str) -> List[str]:
    """Get the command to validate code for a language."""
    lang_cfg = get_language_config(language)
    validator = lang_cfg.validator
    if validator == "python":
        return ["python", "-m", "py_compile"]
    elif validator == "node":
        return ["node", "--check"]
    elif validator == "tsc":
        return ["npx", "tsc", "--noEmit"]
    elif validator == "go":
        return ["go", "vet"]
    elif validator == "rust":
        return ["cargo", "check"]
    elif validator == "java":
        return ["javac", "-Xlint"]
    elif validator == "csharp":
        return ["dotnet", "build"]
    return []


def get_test_command(language: str, test_path: str = None) -> List[str]:
    """Get the command to run tests for a language."""
    lang_cfg = get_language_config(language)
    fw = lang_cfg.test_framework
    if fw == "pytest":
        cmd = ["python", "-m", "pytest", "-v", "--tb=short"]
        if test_path:
            cmd.append(test_path)
        return cmd
    elif fw == "jest":
        cmd = ["npx", "jest", "--verbose"]
        if test_path:
            cmd.append(test_path)
        return cmd
    elif fw == "go test":
        return ["go", "test", "-v", "./..."]
    elif fw == "cargo test":
        return ["cargo", "test"]
    elif fw == "junit":
        return ["./mvnw", "test"] if Path("mvnw").exists() else ["mvn", "test"]
    elif fw == "dotnet test":
        return ["dotnet", "test"]
    return []


def get_build_command(language: str) -> Optional[List[str]]:
    """Get the build command for a language."""
    lang_cfg = get_language_config(language)
    if lang_cfg.build_cmd:
        return lang_cfg.build_cmd.split()
    return None


def get_run_command(language: str, entry_point: str) -> List[str]:
    """Get the run command for a language."""
    lang_cfg = get_language_config(language)
    if language == "python":
        return ["python", entry_point]
    elif language in ("javascript", "typescript"):
        return ["node", entry_point]
    elif language == "go":
        return ["go", "run", entry_point]
    elif language == "rust":
        return ["cargo", "run"]
    elif language == "java":
        class_name = Path(entry_point).stem
        return ["java", class_name]
    elif language == "csharp":
        return ["dotnet", "run", "--project", entry_point]
    return [lang_cfg.run_cmd, entry_point]


def get_package_install_command(language: str, project_dir: Path) -> Optional[List[str]]:
    """Get the command to install dependencies for a language."""
    lang_cfg = get_language_config(language)
    pm = lang_cfg.package_manager
    if pm == "pip":
        req = project_dir / "requirements.txt"
        if req.exists():
            return ["pip", "install", "-r", str(req)]
        pyproject = project_dir / "pyproject.toml"
        if pyproject.exists():
            return ["pip", "install", "-e", "."]
        return ["pip", "install", "-e", "."]
    elif pm == "npm":
        return ["npm", "install"]
    elif pm == "go mod":
        return ["go", "mod", "download"]
    elif pm == "cargo":
        return ["cargo", "fetch"]
    elif pm == "maven":
        return ["./mvnw", "dependency:resolve"] if (project_dir / "mvnw").exists() else ["mvn", "dependency:resolve"]
    elif pm == "nuget":
        return ["dotnet", "restore"]
    return None


LANGUAGE_AGENT_PROMPTS = {
    "python": """
You are a senior Python engineer. Follow Python best practices:
- Type hints for all functions
- Docstrings for public APIs
- Use pathlib over os.path
- Prefer dataclasses/Pydantic for data models
- Async/await for I/O
- pytest for testing
""",
    "javascript": """
You are a senior JavaScript engineer. Follow JS best practices:
- ES modules (import/export)
- JSDoc for public APIs
- ESLint/Prettier compatible
- Jest for testing
- async/await for promises
""",
    "typescript": """
You are a senior TypeScript engineer. Follow TS best practices:
- Strict mode enabled
- Explicit types for public APIs
- Interfaces over types for objects
- Zod for runtime validation
- Jest + ts-jest for testing
""",
    "go": """
You are a senior Go engineer. Follow Go best practices:
- Standard project layout
- Error wrapping with fmt.Errorf
- Context for cancellation
- Table-driven tests
- go vet / staticcheck clean
""",
    "rust": """
You are a senior Rust engineer. Follow Rust best practices:
- Error handling with Result/Option
- Clippy clean code
- Semantic versioning
- cargo test for testing
- Documentation with ///
""",
    "java": """
You are a senior Java engineer. Follow Java best practices:
- Modern Java (17+)
- Records for data carriers
- JUnit 5 for testing
- Maven/Gradle standard layout
- Checkstyle/SpotBugs clean
""",
    "csharp": """
You are a senior C# engineer. Follow C# best practices:
- Modern .NET (8+)
- Nullable reference types
- xUnit for testing
- Source generators where appropriate
- Roslyn analyzers clean
""",
}


def get_language_agent_prompt(language: str) -> str:
    """Get the system prompt addition for a specific language."""
    return LANGUAGE_AGENT_PROMPTS.get(language, LANGUAGE_AGENT_PROMPTS["python"])


def get_file_template(language: str, file_type: str = "source") -> str:
    """Get a starter template for a new file in the given language."""
    templates = {
        "python": {
            "source": '"""Module docstring."""\n\nfrom __future__ import annotations\n\n\ndef main() -> None:\n    pass\n\n\nif __name__ == "__main__":\n    main()\n',
            "test": 'import pytest\n\n\ndef test_example() -> None:\n    assert True\n',
        },
        "javascript": {
            "source": '/** Module description */\n\nfunction main() {\n  // implementation\n}\n\nmain();\n',
            "test": "const { describe, it, expect } = require('@jest/globals');\n\ndescribe('example', () => {\n  it('should work', () => {\n    expect(true).toBe(true);\n  });\n});\n",
        },
        "typescript": {
            "source": '/** Module description */\n\nfunction main(): void {\n  // implementation\n}\n\nmain();\n',
            "test": "import { describe, it, expect } from '@jest/globals';\n\ndescribe('example', () => {\n  it('should work', () => {\n    expect(true).toBe(true);\n  });\n});\n",
        },
        "go": {
            "source": 'package main\n\nimport "fmt"\n\nfunc main() {\n	fmt.Println("Hello, World!")\n}\n',
            "test": 'package main\n\nimport "testing"\n\nfunc TestExample(t *testing.T) {\n	if true != true {\n		t.Fail()\n	}\n}\n',
        },
        "rust": {
            "source": 'fn main() {\n    println!("Hello, World!");\n}\n',
            "test": '#[cfg(test)]\nmod tests {\n    #[test]\n    fn test_example() {\n        assert_eq!(true, true);\n    }\n}\n',
        },
        "java": {
            "source": 'public class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello, World!");\n    }\n}\n',
            "test": 'import org.junit.jupiter.api.Test;\nimport static org.junit.jupiter.api.Assertions.*;\n\nclass MainTest {\n    @Test\n    void testExample() {\n        assertTrue(true);\n    }\n}\n',
        },
        "csharp": {
            "source": 'using System;\n\nclass Program {\n    static void Main() {\n        Console.WriteLine("Hello, World!");\n    }\n}\n',
            "test": 'using Xunit;\n\npublic class ProgramTests {\n    [Fact]\n    public void TestExample() {\n        Assert.True(true);\n    }\n}\n',
        },
    }
    lang_templates = templates.get(language, templates["python"])
    return lang_templates.get(file_type, lang_templates["source"])