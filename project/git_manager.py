from dataclasses import dataclass
from pathlib import Path
import subprocess


@dataclass
class GitStatus:
    repository: bool
    branch: str | None
    head: str | None
    clean: bool
    staged: list[str]
    unstaged: list[str]
    untracked: list[str]


class GitManager:
    """
    Read-only Git inspection and safety checks.

    This class does not:
      - create branches
      - create worktrees
      - commit
      - reset
      - checkout
      - modify files
    """

    def __init__(self, root="~/MyAI"):
        self.root = Path(root).expanduser().resolve()

    def is_repository(self):
        result = self._run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            check=False,
        )

        return (
            result.returncode == 0
            and result.stdout.strip() == "true"
        )

    def current_branch(self):
        result = self._run(
            ["git", "branch", "--show-current"],
            check=False,
        )

        if result.returncode != 0:
            return None

        branch = result.stdout.strip()

        return branch or None

    def head(self):
        result = self._run(
            ["git", "rev-parse", "HEAD"],
            check=False,
        )

        if result.returncode != 0:
            return None

        value = result.stdout.strip()

        return value or None

    def status(self):
        if not self.is_repository():
            return GitStatus(
                repository=False,
                branch=None,
                head=None,
                clean=False,
                staged=[],
                unstaged=[],
                untracked=[],
            )

        result = self._run(
            [
                "git",
                "status",
                "--porcelain=v1",
            ],
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                result.stderr.strip()
                or "Unable to read Git status."
            )

        staged = []
        unstaged = []
        untracked = []

        for line in result.stdout.splitlines():
            if not line:
                continue

            code = line[:2]
            path = line[3:]

            if code == "??":
                untracked.append(path)
                continue

            if code[0] != " ":
                staged.append(path)

            if code[1] != " ":
                unstaged.append(path)

        clean = not (
            staged
            or unstaged
            or untracked
        )

        return GitStatus(
            repository=True,
            branch=self.current_branch(),
            head=self.head(),
            clean=clean,
            staged=staged,
            unstaged=unstaged,
            untracked=untracked,
        )

    def safety_check(self):
        """
        Determine whether an automatic repair may safely begin.

        This is intentionally conservative.
        """
        status = self.status()

        if not status.repository:
            return {
                "safe": False,
                "reason": "Directory is not a Git repository.",
                "status": status,
            }

        if status.head is None:
            return {
                "safe": False,
                "reason": "Repository has no valid HEAD.",
                "status": status,
            }

        if status.branch is None:
            return {
                "safe": False,
                "reason": "Repository is in detached HEAD state.",
                "status": status,
            }

        # We do not block manual inspection, but automatic repair should
        # not silently mix with pre-existing user changes.
        if not status.clean:
            return {
                "safe": False,
                "reason": (
                    "Working tree contains existing changes. "
                    "Automatic repair must be isolated first."
                ),
                "status": status,
            }

        return {
            "safe": True,
            "reason": "Repository is clean and on a named branch.",
            "status": status,
        }


    def create_worktree(self, worktree_path: str, branch_name: str):
        """Create an isolated worktree from the current HEAD."""
        worktree = Path(worktree_path).expanduser().resolve()

        if not branch_name or branch_name.strip() != branch_name:
            return {"success": False, "error": "Invalid branch name."}

        if branch_name in {"main", "master"}:
            return {
                "success": False,
                "error": "Refusing to use a protected branch name.",
            }

        if worktree == self.root:
            return {
                "success": False,
                "error": "Worktree path cannot be the main repository.",
            }

        if worktree.exists():
            return {
                "success": False,
                "error": f"Worktree path already exists: {worktree}",
            }

        branch_result = self._run(
            ["git", "branch", "--list", branch_name],
            check=False,
        )

        if branch_result.returncode != 0:
            return {
                "success": False,
                "error": (
                    branch_result.stderr.strip()
                    or "Unable to inspect Git branches."
                ),
            }

        if branch_result.stdout.strip():
            return {
                "success": False,
                "error": f"Branch already exists: {branch_name}",
            }

        result = self._run(
            [
                "git",
                "worktree",
                "add",
                "-b",
                branch_name,
                str(worktree),
                "HEAD",
            ],
            check=False,
        )

        if result.returncode != 0:
            return {
                "success": False,
                "error": (
                    result.stderr.strip()
                    or result.stdout.strip()
                    or "Unable to create worktree."
                ),
            }

        return {
            "success": True,
            "path": str(worktree),
            "branch": branch_name,
            "head": self.head(),
        }

    def remove_worktree(self, worktree_path: str):
        """Remove an isolated worktree."""
        worktree = Path(worktree_path).expanduser().resolve()

        if worktree == self.root:
            return {
                "success": False,
                "error": "Refusing to remove the main repository.",
            }

        if not worktree.exists():
            return {
                "success": False,
                "error": f"Worktree does not exist: {worktree}",
            }

        result = self._run(
            [
                "git",
                "worktree",
                "remove",
                "--force",
                str(worktree),
            ],
            check=False,
        )

        if result.returncode != 0:
            return {
                "success": False,
                "error": (
                    result.stderr.strip()
                    or result.stdout.strip()
                    or "Unable to remove worktree."
                ),
            }

        return {
            "success": True,
            "path": str(worktree),
        }

    def delete_branch(self, branch_name: str):
        """Delete an isolated local branch safely."""
        current = self.current_branch()

        if not branch_name:
            return {
                "success": False,
                "error": "Branch name is required.",
            }

        if branch_name == current:
            return {
                "success": False,
                "error": "Refusing to delete the current branch.",
            }

        result = self._run(
            ["git", "branch", "-D", branch_name],
            check=False,
        )

        if result.returncode != 0:
            return {
                "success": False,
                "error": (
                    result.stderr.strip()
                    or result.stdout.strip()
                    or "Unable to delete branch."
                ),
            }

        return {
            "success": True,
            "branch": branch_name,
        }

    def diff(self):
        result = self._run(
            ["git", "diff", "--"],
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                result.stderr.strip()
                or "Unable to read Git diff."
            )

        return result.stdout

    def staged_diff(self):
        result = self._run(
            ["git", "diff", "--cached", "--"],
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                result.stderr.strip()
                or "Unable to read staged Git diff."
            )

        return result.stdout

    def _run(self, args, check=True):
        return subprocess.run(
            args,
            cwd=self.root,
            capture_output=True,
            text=True,
            check=check,
        )
