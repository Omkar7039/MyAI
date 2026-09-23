from __future__ import annotations

import hashlib
from pathlib import Path

from tools.base import ToolResult
from tools.workspace import Workspace


class FileHashTool:
    """
    Calculate a cryptographic hash for a file inside the workspace.
    """

    name = "file_hash"

    description = (
        "Calculate the SHA-256 hash of a local file inside the allowed workspace."
    )

    def __init__(
        self,
        base_directory: str | Path | None = None,
        workspace: Workspace | None = None,
    ):
        if workspace is not None and base_directory is not None:
            raise ValueError(
                "Provide either workspace or base_directory, not both."
            )

        self.workspace = (
            workspace
            if workspace is not None
            else Workspace(base_directory)
        )

    @property
    def base_directory(self) -> Path:
        return self.workspace.root

    @base_directory.setter
    def base_directory(self, value: str | Path) -> None:
        self.workspace = Workspace(value)

    def execute(self, path: str) -> ToolResult:
        try:
            if not path.strip():
                raise ValueError("No file path supplied.")

            try:
                resolved = self.workspace.resolve(path)
            except ValueError as exc:
                if str(exc) == "Path is outside the allowed workspace.":
                    raise ValueError(
                        "Path is outside the allowed base directory."
                    )
                raise

            if not resolved.exists():
                raise ValueError(
                    f"File does not exist: {path}"
                )

            if not resolved.is_file():
                raise ValueError(
                    f"Path is not a file: {path}"
                )

            digest = hashlib.sha256()

            with resolved.open("rb") as file:
                for chunk in iter(lambda: file.read(1024 * 1024), b""):
                    digest.update(chunk)

            return ToolResult(
                tool_name=self.name,
                success=True,
                result={
                    "path": str(
                        resolved.relative_to(
                            self.workspace.root
                        )
                    ),
                    "algorithm": "sha256",
                    "hash": digest.hexdigest(),
                },
            )

        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=str(exc),
            )
