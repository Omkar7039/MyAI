from __future__ import annotations

from pathlib import Path

from tools.base import ToolResult
from tools.workspace import Workspace


class WriteFileTool:
    """
    Explicit file-writing tool constrained to the MyAI workspace.
    """

    name = "write_file"

    description = (
        "Write text content to a local file inside the allowed workspace."
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
        content: str,
    ) -> ToolResult:
        try:
            if not path.strip():
                raise ValueError(
                    "No file path supplied."
                )

            try:
                resolved = self.workspace.resolve(path)
            except ValueError as exc:
                if str(exc) == "Path is outside the allowed workspace.":
                    raise ValueError(
                        "Path is outside the allowed base directory."
                    )
                raise

            if resolved.exists() and resolved.is_dir():
                raise ValueError(
                    f"Path is not a file: {path}"
                )

            resolved.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            resolved.write_text(
                content,
                encoding="utf-8",
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
                    "bytes": resolved.stat().st_size,
                },
            )

        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=str(exc),
            )
