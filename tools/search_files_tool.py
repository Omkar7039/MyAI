from __future__ import annotations

from pathlib import Path

from tools.base import ToolResult
from tools.workspace import Workspace


class SearchFilesTool:
    """
    Explicit read-only text search tool for project files.
    """

    name = "search_files"

    description = (
        "Search text across files inside an allowed local directory."
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
        query: str,
        path: str = ".",
    ) -> ToolResult:
        try:
            if not query.strip():
                raise ValueError(
                    "No search query supplied."
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
                    f"Search path does not exist: {path}"
                )

            matches = []

            files = (
                [resolved]
                if resolved.is_file()
                else sorted(
                    item
                    for item in resolved.rglob("*")
                    if item.is_file()
                )
            )

            for file_path in files:
                try:
                    relative_path = file_path.relative_to(
                        self.workspace.root
                    )

                    text = file_path.read_text(
                        encoding="utf-8"
                    )

                except (
                    UnicodeDecodeError,
                    OSError,
                ):
                    continue

                for line_number, line in enumerate(
                    text.splitlines(),
                    start=1,
                ):
                    if query in line:
                        matches.append(
                            {
                                "path": str(relative_path),
                                "line": line_number,
                                "text": line,
                            }
                        )

            return ToolResult(
                tool_name=self.name,
                success=True,
                result=matches,
            )

        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=str(exc),
            )
