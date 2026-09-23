from __future__ import annotations

from pathlib import Path

from tools.base import ToolResult
from tools.workspace import Workspace


class GetFileInfoTool:
    """
    Return metadata about a file or directory inside the workspace.
    """

    name = "get_file_info"

    description = (
        "Get metadata about a local file or directory inside the allowed workspace."
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

            if not resolved.exists():
                raise ValueError(
                    f"Path does not exist: {path}"
                )

            stat = resolved.stat()

            if resolved.is_file():
                item_type = "file"
                child_count = None
            elif resolved.is_dir():
                item_type = "directory"
                child_count = sum(1 for _ in resolved.iterdir())
            else:
                item_type = "other"
                child_count = None

            return ToolResult(
                tool_name=self.name,
                success=True,
                result={
                    "path": str(
                        resolved.relative_to(
                            self.workspace.root
                        )
                    ),
                    "type": item_type,
                    "size": stat.st_size,
                    "modified_time": stat.st_mtime,
                    "child_count": child_count,
                },
            )

        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=str(exc),
            )
