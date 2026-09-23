from __future__ import annotations

from pathlib import Path

from tools.base import ToolResult
from tools.workspace import Workspace


class FileExistsTool:
    """
    Check whether a file or directory exists inside the allowed workspace.
    """

    name = "file_exists"

    description = (
        "Check whether a local file or directory exists inside the allowed workspace."
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
                raise ValueError("No path supplied.")

            try:
                resolved = self.workspace.resolve(path)
            except ValueError as exc:
                if str(exc) == "Path is outside the allowed workspace.":
                    raise ValueError(
                        "Path is outside the allowed base directory."
                    )
                raise

            exists = resolved.exists()

            if resolved.is_file():
                item_type = "file"
            elif resolved.is_dir():
                item_type = "directory"
            else:
                item_type = None

            return ToolResult(
                tool_name=self.name,
                success=True,
                result={
                    "path": str(
                        resolved.relative_to(
                            self.workspace.root
                        )
                    ),
                    "exists": exists,
                    "type": item_type,
                },
            )

        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=str(exc),
            )
