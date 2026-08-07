"""
utils/git_integration.py
Git integration for committing and pushing generated code
"""

import subprocess
import logging
import os
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass

import config

logger = logging.getLogger(__name__)


@dataclass
class GitConfig:
    """Git configuration for a project"""
    repo_url: str = ""
    branch: str = "main"
    username: str = "AgentForge"
    email: str = "agentforge@local"
    ssh_key_path: Optional[str] = None
    commit_message_prefix: str = "AgentForge: "
    auto_push: bool = False
    remote_name: str = "origin"


@dataclass
class GitStatus:
    """Status of git repository"""
    is_repo: bool = False
    current_branch: str = ""
    has_changes: bool = False
    staged_files: List[str] = None
    unstaged_files: List[str] = None
    untracked_files: List[str] = None
    ahead: int = 0
    behind: int = 0
    last_commit: str = ""

    def __post_init__(self):
        if self.staged_files is None:
            self.staged_files = []
        if self.unstaged_files is None:
            self.unstaged_files = []
        if self.untracked_files is None:
            self.untracked_files = []


class GitIntegration:
    """Handles git operations for generated projects"""

    def __init__(self, project_dir: Path = None, git_config: GitConfig = None):
        self.project_dir = project_dir or config.PROJECT_DIR
        self.git_config = git_config or GitConfig()
        self._ensure_git_available()

    def _ensure_git_available(self):
        """Check if git is available"""
        try:
            subprocess.run(["git", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("Git not found. Please install git.")

    def _run_git(self, args: List[str], cwd: Path = None) -> Tuple[int, str, str]:
        """Run git command and return (returncode, stdout, stderr)"""
        cwd = cwd or self.project_dir
        env = os.environ.copy()
        if self.git_config.ssh_key_path:
            env["GIT_SSH_COMMAND"] = f"ssh -i {self.git_config.ssh_key_path}"

        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=60,
                env=env
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", "Git command timed out"
        except Exception as e:
            return -1, "", str(e)

    def init_repo(self, remote_url: str = None) -> bool:
        """Initialize git repository"""
        # Check if already a repo
        if (self.project_dir / ".git").exists():
            logger.info("Git repository already exists")
            return True

        # Initialize
        code, out, err = self._run_git(["init"])
        if code != 0:
            logger.error(f"Failed to init repo: {err}")
            return False

        # Configure user
        self._run_git(["config", "user.name", self.git_config.username])
        self._run_git(["config", "user.email", self.git_config.email])

        # Add remote if provided
        if remote_url or self.git_config.repo_url:
            remote = remote_url or self.git_config.repo_url
            self._run_git(["remote", "add", self.git_config.remote_name, remote])

        # Create initial commit if there are files
        files = list(self.project_dir.rglob("*"))
        if any(f.is_file() for f in files):
            self._run_git(["add", "-A"])
            self._run_git(["commit", "-m", f"{self.git_config.commit_message_prefix}Initial commit"])

        logger.info("Git repository initialized")
        return True

    def get_status(self) -> GitStatus:
        """Get current git status"""
        status = GitStatus()

        # Check if git repo
        code, _, _ = self._run_git(["rev-parse", "--git-dir"])
        if code != 0:
            return status

        status.is_repo = True

        # Current branch
        code, out, _ = self._run_git(["branch", "--show-current"])
        if code == 0:
            status.current_branch = out

        # Status porcelain
        code, out, _ = self._run_git(["status", "--porcelain"])
        if code == 0 and out:
            for line in out.split('\n'):
                if not line:
                    continue
                status_code = line[:2]
                filepath = line[3:]
                if status_code[0] in ('M', 'A', 'D', 'R', 'C'):
                    status.staged_files.append(filepath)
                if status_code[1] in ('M', 'D'):
                    status.unstaged_files.append(filepath)
                if status_code == '??':
                    status.untracked_files.append(filepath)

        status.has_changes = bool(status.staged_files or status.unstaged_files or status.untracked_files)

        # Check ahead/behind
        if self.git_config.repo_url:
            self._run_git(["fetch", self.git_config.remote_name])
            code, out, _ = self._run_git(["rev-list", "--left-right", "--count", f"{self.git_config.remote_name}/{self.git_config.branch}...HEAD"])
            if code == 0 and out:
                parts = out.split('\t')
                if len(parts) == 2:
                    status.ahead = int(parts[0])
                    status.behind = int(parts[1])

        # Last commit
        code, out, _ = self._run_git(["log", "-1", "--pretty=format:%h %s"])
        if code == 0:
            status.last_commit = out

        return status

    def commit_all(self, message: str = None, files: List[str] = None) -> Tuple[bool, str]:
        """Stage and commit all changes"""
        if files:
            for f in files:
                code, _, err = self._run_git(["add", f])
                if code != 0:
                    return False, f"Failed to add {f}: {err}"
        else:
            code, _, err = self._run_git(["add", "-A"])
            if code != 0:
                return False, f"Failed to add files: {err}"

        commit_msg = message or f"{self.git_config.commit_message_prefix}Auto-commit generated files"
        code, out, err = self._run_git(["commit", "-m", commit_msg])
        if code != 0:
            if "nothing to commit" in err.lower():
                return True, "No changes to commit"
            return False, f"Commit failed: {err}"

        return True, out

    def push(self, force: bool = False) -> Tuple[bool, str]:
        """Push commits to remote"""
        if not self.git_config.repo_url:
            return False, "No remote URL configured"

        args = ["push", self.git_config.remote_name, self.git_config.branch]
        if force:
            args.append("--force")

        code, out, err = self._run_git(args)
        if code != 0:
            return False, f"Push failed: {err}"

        return True, out

    def pull(self, rebase: bool = False) -> Tuple[bool, str]:
        """Pull changes from remote"""
        if not self.git_config.repo_url:
            return False, "No remote URL configured"

        args = ["pull", self.git_config.remote_name, self.git_config.branch]
        if rebase:
            args.append("--rebase")

        code, out, err = self._run_git(args)
        if code != 0:
            return False, f"Pull failed: {err}"

        return True, out

    def create_branch(self, branch_name: str, checkout: bool = True) -> Tuple[bool, str]:
        """Create and optionally checkout a new branch"""
        args = ["checkout", "-b", branch_name] if checkout else ["branch", branch_name]
        code, out, err = self._run_git(args)
        if code != 0:
            return False, f"Branch creation failed: {err}"
        return True, out

    def checkout(self, branch_name: str) -> Tuple[bool, str]:
        """Checkout existing branch"""
        code, out, err = self._run_git(["checkout", branch_name])
        if code != 0:
            return False, f"Checkout failed: {err}"
        return True, out

    def get_diff(self, staged: bool = False) -> str:
        """Get diff of changes"""
        args = ["diff"]
        if staged:
            args.append("--cached")
        code, out, err = self._run_git(args)
        return out if code == 0 else err

    def get_log(self, count: int = 10) -> List[dict]:
        """Get recent commit log"""
        code, out, err = self._run_git(["log", f"-{count}", "--pretty=format:%H|%h|%an|%ae|%at|%s"])
        if code != 0:
            return []

        commits = []
        for line in out.split('\n'):
            if not line:
                continue
            parts = line.split('|', 5)
            if len(parts) == 6:
                commits.append({
                    "hash": parts[0],
                    "short_hash": parts[1],
                    "author_name": parts[2],
                    "author_email": parts[3],
                    "timestamp": int(parts[4]),
                    "message": parts[5]
                })
        return commits

    def add_remote(self, name: str, url: str) -> Tuple[bool, str]:
        """Add a git remote"""
        self.git_config.repo_url = url
        self.git_config.remote_name = name
        code, out, err = self._run_git(["remote", "add", name, url])
        if code != 0:
            return False, f"Add remote failed: {err}"
        return True, out

    def setup_ssh_key(self, key_path: str) -> bool:
        """Configure SSH key for git operations"""
        if Path(key_path).exists():
            self.git_config.ssh_key_path = key_path
            return True
        return False


def auto_commit_generated(project_dir: Path = None, message: str = None, push: bool = False,
                         repo_url: str = None, branch: str = "main") -> Tuple[bool, str]:
    """
    Convenience function to auto-commit generated project files

    Args:
        project_dir: Project directory (default: config.PROJECT_DIR)
        message: Custom commit message
        push: Whether to push after commit
        repo_url: Remote repository URL
        branch: Branch name

    Returns:
        (success, message)
    """
    git_config = GitConfig(
        repo_url=repo_url or "",
        branch=branch,
        auto_push=push
    )

    git = GitIntegration(project_dir, git_config)

    # Initialize if needed
    if not (project_dir or config.PROJECT_DIR).joinpath(".git").exists():
        if not git.init_repo(repo_url):
            return False, "Failed to initialize git repository"

    # Commit changes
    success, msg = git.commit_all(message)
    if not success:
        return False, msg

    # Push if requested
    if push and repo_url:
        success, msg = git.push()
        if not success:
            return False, msg

    return True, msg


# Integration with autonomous agent
class GitAgentCallbacks:
    """Callbacks for autonomous agent to auto-commit on milestones"""

    def __init__(self, git_integration: GitIntegration, commit_on_goal: bool = True,
                 commit_on_iteration: int = 5, push_on_commit: bool = False):
        self.git = git_integration
        self.commit_on_goal = commit_on_goal
        self.commit_on_iteration = commit_on_iteration
        self.push_on_commit = push_on_commit
        self.iteration_count = 0

    def on_goal_complete(self, goal):
        """Called when a goal is completed"""
        if self.commit_on_goal:
            msg = f"{self.git.git_config.commit_message_prefix}Completed goal: {goal.description[:80]}"
            success, result = self.git.commit_all(msg)
            if success and "No changes" not in result:
                logger.info(f"Auto-committed on goal completion: {result}")
                if self.push_on_commit:
                    self.git.push()

    def on_task_complete(self, task):
        """Called when a task is completed"""
        self.iteration_count += 1
        if self.commit_on_iteration and self.iteration_count % self.commit_on_iteration == 0:
            msg = f"{self.git.git_config.commit_message_prefix}Iteration {self.iteration_count}: completed task {task.id}"
            success, result = self.git.commit_all(msg)
            if success and "No changes" not in result:
                logger.info(f"Auto-committed on iteration {self.iteration_count}: {result}")
                if self.push_on_commit:
                    self.git.push()

    def on_error(self, task, error):
        """Called when a task fails"""
        pass  # Don't commit on errors