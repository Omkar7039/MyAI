from __future__ import annotations

from pathlib import Path

from tools.base import ToolResult
from tools.workspace import Workspace


class EditFileTool:
    """
    Explicit targeted file-editing tool constrained to the workspace.
    """

    name = "edit_file"

    description = (
        "Replace one exact text block inside a local workspace file."
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
        old_text: str,
        new_text: str,
    ) -> ToolResult:
        try:
            if not path.strip():
                raise ValueError(
                    "No file path supplied."
                )

            if not old_text:
                raise ValueError(
                    "No old text supplied."
                )

            resolved = self.workspace.resolve(path)

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

            occurrences = content.count(old_text)

            if occurrences == 0:
                raise ValueError(
                    "The old text was not found in the file."
                )

            if occurrences > 1:
                raise ValueError(
                    "The old text occurs multiple times; "
                    "the edit is ambiguous."
                )

            updated = content.replace(
                old_text,
                new_text,
                1,
            )

            resolved.write_text(
                updated,
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
                    "replacements": 1,
                },
            )

        except ValueError as exc:
            if str(exc) == "Path is outside the allowed workspace.":
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=(
                        "Path is outside the allowed "
                        "base directory."
                    ),
                )

            return ToolResult(
                tool_name=self.name,
                success=False,
                error=str(exc),
            )

        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=str(exc),
            )
