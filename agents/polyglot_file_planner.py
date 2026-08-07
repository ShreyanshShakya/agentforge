"""
agents/polyglot_file_planner.py
Multi-language file planner that generates project structures for any supported language.
"""

import json
from typing import Dict, List, Any, Optional

from agents.base_agent import BaseAgent
import config
from utils.language import detect_language, get_language_config, LANGUAGE_CONFIGS


class PolyglotFilePlannerAgent(BaseAgent):
    """File planner that supports multiple programming languages."""

    def __init__(self, model: str = None, target_language: str = None):
        super().__init__(
            name="Polyglot File Planner",
            model=model or config.DEFAULT_PLANNER_MODEL,
            num_predict=config.NUM_PREDICT["file_planner"],
            system_prompt=self._build_system_prompt(target_language),
        )
        self.target_language = target_language

    def _build_system_prompt(self, target_language: str = None) -> str:
        """Build system prompt with language-specific guidance."""
        lang = target_language or config.DEFAULT_LANGUAGE
        lang_cfg = get_language_config(lang)

        # Get language-specific file patterns
        config_files = lang_cfg.config_files
        extensions = lang_cfg.extensions
        test_pattern = lang_cfg.test_pattern

        lang_examples = {
            "python": {
                "config_files": ["requirements.txt", "pyproject.toml"],
                "source_dirs": ["app/", "src/"],
                "test_dir": "tests/",
                "entry_points": ["main.py", "app/main.py"],
            },
            "javascript": {
                "config_files": ["package.json"],
                "source_dirs": ["src/"],
                "test_dir": "tests/",
                "entry_points": ["src/index.js", "index.js"],
            },
            "typescript": {
                "config_files": ["package.json", "tsconfig.json"],
                "source_dirs": ["src/"],
                "test_dir": "tests/",
                "entry_points": ["src/index.ts", "index.ts"],
            },
            "go": {
                "config_files": ["go.mod", "go.sum"],
                "source_dirs": ["cmd/", "internal/", "pkg/"],
                "test_dir": "same as source (*_test.go)",
                "entry_points": ["cmd/main.go", "main.go"],
            },
            "rust": {
                "config_files": ["Cargo.toml"],
                "source_dirs": ["src/"],
                "test_dir": "tests/ or src/ (integration)",
                "entry_points": ["src/main.rs"],
            },
            "java": {
                "config_files": ["pom.xml", "build.gradle"],
                "source_dirs": ["src/main/java/"],
                "test_dir": "src/test/java/",
                "entry_points": ["src/main/java/com/example/Main.java"],
            },
            "csharp": {
                "config_files": ["*.csproj", "*.sln"],
                "source_dirs": ["src/"],
                "test_dir": "tests/",
                "entry_points": ["src/Program.cs"],
            },
        }

        example = lang_examples.get(lang, lang_examples["python"])

        return f"""
You are a multi-language software architect.

Given a technical specification, generate a complete project file structure for {lang.upper()}.

Language Configuration:
- Extensions: {', '.join(extensions)}
- Config Files: {', '.join(config_files)}
- Test Pattern: {test_pattern}
- Test Framework: {lang_cfg.test_framework}
- Package Manager: {lang_cfg.package_manager}

Typical {lang.upper()} Project Structure:
{json.dumps(example, indent=2)}

Output ONLY valid JSON with this schema:

{{
  "project_name": "string",
  "language": "{lang}",
  "files": [
    {{
      "path": "string",
      "description": "string",
      "depends_on": ["string", ...],
      "language": "{lang}",
      "file_type": "config|source|test|docs|other"
    }}
  ]
}}

Rules:
1. Include ALL necessary config files for {lang}
2. Use correct file extensions for {lang}
3. Follow {lang} project layout conventions
4. Add depends_on for import dependencies
5. Include test files matching {test_pattern}
6. Mark file_type appropriately
7. Entry point should have no depends_on (or minimal)
"""


class PolyglotFilePlanner:
    """High-level interface for polyglot file planning."""

    def __init__(self, model: str = None):
        self.model = model or config.DEFAULT_PLANNER_MODEL
        self.agents: Dict[str, PolyglotFilePlannerAgent] = {}

    def get_agent(self, language: str) -> PolyglotFilePlannerAgent:
        """Get or create agent for a language."""
        if language not in self.agents:
            self.agents[language] = PolyglotFilePlannerAgent(self.model, language)
        return self.agents[language]

    def plan(
        self,
        specification: str,
        language: str = None,
        project_dir: str = None
    ) -> Dict[str, Any]:
        """
        Generate a file plan for the given specification and language.

        Args:
            specification: The technical specification from consensus
            language: Target language (auto-detected if not specified)
            project_dir: Optional project directory for context

        Returns:
            Parsed file plan dictionary
        """
        # Auto-detect language if not specified
        if language is None and project_dir:
            from pathlib import Path
            language = detect_language(Path(project_dir))
        elif language is None:
            language = config.DEFAULT_LANGUAGE

        agent = self.get_agent(language)

        prompt = f"""
Technical Specification:
{specification}

Target Language: {language}

Generate the complete file plan as JSON.
"""
        raw_output = agent.run(prompt, use_cache=False)

        try:
            parsed = json.loads(raw_output)
            # Validate and enhance
            return self._validate_and_enhance(parsed, language)
        except json.JSONDecodeError as e:
            # Try to extract JSON from markdown
            import re
            match = re.search(r'\{.*\}', raw_output, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group())
                    return self._validate_and_enhance(parsed, language)
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Failed to parse file plan JSON: {e}")

    def _validate_and_enhance(self, plan: Dict[str, Any], language: str) -> Dict[str, Any]:
        """Validate plan and add defaults."""
        lang_cfg = get_language_config(language)

        # Ensure required fields
        plan.setdefault("project_name", "project")
        plan.setdefault("language", language)
        plan.setdefault("files", [])

        # Validate each file entry
        enhanced_files = []
        for f in plan["files"]:
            if isinstance(f, str):
                # Simple path string
                enhanced_files.append({
                    "path": f,
                    "description": f"File: {f}",
                    "depends_on": [],
                    "language": language,
                    "file_type": self._infer_file_type(f, language),
                })
            elif isinstance(f, dict):
                enhanced = {
                    "path": f.get("path", ""),
                    "description": f.get("description", ""),
                    "depends_on": f.get("depends_on", []),
                    "language": f.get("language", language),
                    "file_type": f.get("file_type", self._infer_file_type(f.get("path", ""), language)),
                }
                enhanced_files.append(enhanced)

        plan["files"] = enhanced_files

        # Ensure config files exist
        self._ensure_config_files(plan, language, lang_cfg)

        # Ensure test files for source files
        self._ensure_test_files(plan, language, lang_cfg)

        return plan

    def _infer_file_type(self, path: str, language: str) -> str:
        """Infer file type from path and language."""
        path_lower = path.lower()
        lang_cfg = get_language_config(language)

        # Config files
        for cf in lang_cfg.config_files:
            if cf.replace("*", "").replace("?", "") in path_lower:
                return "config"

        # Test files
        test_pattern = lang_cfg.test_pattern.replace("*", "").replace("?", "")
        if test_pattern and test_pattern in path_lower:
            return "test"
        if path_lower.startswith("test_") or path_lower.endswith("_test.py"):
            return "test"
        if "test" in path_lower and path_lower.endswith(tuple(lang_cfg.extensions)):
            return "test"

        # Source files
        if any(path_lower.endswith(ext) for ext in lang_cfg.extensions):
            return "source"

        # Docs
        if path_lower.endswith((".md", ".rst", ".txt", ".adoc")):
            return "docs"

        return "other"

    def _ensure_config_files(self, plan: Dict[str, Any], language: str, lang_cfg):
        """Ensure required config files are in the plan."""
        existing_paths = {f["path"] for f in plan["files"]}

        for cf in lang_cfg.config_files:
            # Handle glob patterns
            if "*" in cf or "?" in cf:
                # Skip glob patterns, they'll be created by package init
                continue
            if cf not in existing_paths:
                plan["files"].append({
                    "path": cf,
                    "description": f"{language.upper()} configuration file",
                    "depends_on": [],
                    "language": language,
                    "file_type": "config",
                })

    def _ensure_test_files(self, plan: Dict[str, Any], language: str, lang_cfg):
        """Ensure test files exist for source files."""
        source_files = [f for f in plan["files"] if f["file_type"] == "source"]
        existing_paths = {f["path"] for f in plan["files"]}

        for sf in source_files:
            test_name = lang_cfg.get_test_filename(sf["path"])
            test_path = self._get_test_path(sf["path"], test_name, language)

            if test_path not in existing_paths:
                plan["files"].append({
                    "path": test_path,
                    "description": f"Tests for {sf['path']}",
                    "depends_on": [sf["path"]],
                    "language": language,
                    "file_type": "test",
                })

    def _get_test_path(self, source_path: str, test_name: str, language: str) -> str:
        """Determine test file path based on language conventions."""
        from pathlib import Path

        source = Path(source_path)
        lang_cfg = get_language_config(language)

        if language == "python":
            return f"tests/{source.parent.name}/{test_name}" if source.parent.name != "." else f"tests/{test_name}"
        elif language in ("javascript", "typescript"):
            return f"tests/{test_name}"
        elif language == "go":
            return str(source.parent / test_name)
        elif language == "rust":
            if "src/" in source_path:
                return source_path.replace("src/", "tests/").replace(source.name, test_name)
            return f"tests/{test_name}"
        elif language == "java":
            return source_path.replace("src/main/", "src/test/").replace(source.name, test_name)
        elif language == "csharp":
            return f"tests/{test_name}"

        return f"tests/{test_name}"


# Convenience function
def create_polyglot_file_plan(
    specification: str,
    language: str = None,
    model: str = None,
    project_dir: str = None
) -> Dict[str, Any]:
    """Create a polyglot file plan."""
    planner = PolyglotFilePlanner(model)
    return planner.plan(specification, language, project_dir)