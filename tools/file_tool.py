from __future__ import annotations

from pathlib import Path

from tools.base import ToolResult
from tools.workspace import Workspace


class ReadFileTool:
    """
    Explicit read-only file inspection tool.
    """

    name = "read_file"

    description = (
        "Read text content from a local file, optionally limited to a line range."
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
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> ToolResult:
        try:
            if not path.strip():
                raise ValueError(
                    "No file path supplied."
                )

            if start_line is not None:
                if isinstance(start_line, bool) or not isinstance(start_line, int):
                    raise ValueError(
                        "start_line must be an integer."
                    )
                if start_line < 1:
                    raise ValueError(
                        "start_line must be at least 1."
                    )

            if end_line is not None:
                if isinstance(end_line, bool) or not isinstance(end_line, int):
                    raise ValueError(
                        "end_line must be an integer."
                    )
                if end_line < 1:
                    raise ValueError(
                        "end_line must be at least 1."
                    )

            if (
                start_line is not None
                and end_line is not None
                and start_line > end_line
            ):
                raise ValueError(
                    "start_line cannot be greater than end_line."
                )

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

            content = resolved.read_text(
                encoding="utf-8"
            )

            if start_line is None and end_line is None:
                result = content
            else:
                lines = content.splitlines(keepends=True)

                first = (
                    start_line - 1
                    if start_line is not None
                    else 0
                )

                last = (
                    end_line
                    if end_line is not None
                    else len(lines)
                )

                result = "".join(lines[first:last])

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
