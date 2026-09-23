from __future__ import annotations

from pathlib import Path

from tools.base import ToolResult
from tools.workspace import Workspace


class ListFilesTool:
    """
    Explicit read-only directory listing tool.
    """

    name = "list_files"

    description = (
        "List files and directories inside an allowed local directory."
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
        path: str = ".",
    ) -> ToolResult:
        try:
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
                    f"Directory does not exist: {path}"
                )

            if not resolved.is_dir():
                raise ValueError(
                    f"Path is not a directory: {path}"
                )

            entries = sorted(
                resolved.iterdir(),
                key=lambda item: (
                    not item.is_dir(),
                    item.name.lower(),
                ),
            )

            result = [
                {
                    "name": entry.name,
                    "type": (
                        "directory"
                        if entry.is_dir()
                        else "file"
                    ),
                }
                for entry in entries
            ]

            return ToolResult(
                tool_name=self.name,
                success=True,
                result=result,
            )

        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=str(exc),
            )
