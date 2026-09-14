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
