from __future__ import annotations

from pathlib import Path

from tools.base import ToolResult
from tools.workspace import Workspace


class CreateDirectoryTool:
    """
    Explicit directory-creation tool constrained to the workspace.
    """

    name = "create_directory"

    description = (
        "Create a directory inside the allowed workspace."
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

    def execute(
        self,
        path: str,
    ) -> ToolResult:
        try:
            if not path.strip():
                raise ValueError(
                    "No directory path supplied."
                )

            try:
                resolved = self.workspace.resolve(path)
            except ValueError as exc:
                if str(exc) == "Path is outside the allowed workspace.":
                    raise ValueError(
                        "Path is outside the allowed base directory."
                    )
                raise

            if resolved.exists():
                if resolved.is_dir():
                    raise ValueError(
                        f"Directory already exists: {path}"
                    )

                raise ValueError(
                    f"Path already exists and is not a directory: {path}"
                )

            resolved.mkdir(
                parents=True,
                exist_ok=False,
            )

            return ToolResult(
                tool_name=self.name,
                success=True,
                result={
                    "path": str(
                        resolved.relative_to(
                            self.workspace.root
                        )
                    ),
                    "created": True,
                },
            )

        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=str(exc),
            )
