from __future__ import annotations

import shutil
from pathlib import Path

from tools.base import ToolResult
from tools.workspace import Workspace


class CopyFileTool:
    """
    Copy a file or directory inside the allowed workspace.
    """

    name = "copy_file"

    description = (
        "Copy a local file or directory inside the allowed workspace."
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
        source: str,
        destination: str,
    ) -> ToolResult:
        try:
            if not source.strip():
                raise ValueError("No source path supplied.")

            if not destination.strip():
                raise ValueError("No destination path supplied.")

            try:
                resolved_source = self.workspace.resolve(source)
                resolved_destination = self.workspace.resolve(destination)
            except ValueError as exc:
                if str(exc) == "Path is outside the allowed workspace.":
                    raise ValueError(
                        "Path is outside the allowed base directory."
                    )
                raise

            if not resolved_source.exists():
                raise ValueError(
                    f"Source path does not exist: {source}"
                )

            if resolved_destination.exists():
                raise ValueError(
                    f"Destination already exists: {destination}"
                )

            resolved_destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            if resolved_source.is_dir():
                shutil.copytree(
                    resolved_source,
                    resolved_destination,
                )
            else:
                shutil.copy2(
                    resolved_source,
                    resolved_destination,
                )

            return ToolResult(
                tool_name=self.name,
                success=True,
                result={
                    "source": str(
                        resolved_source.relative_to(
                            self.workspace.root
                        )
                    ),
                    "destination": str(
                        resolved_destination.relative_to(
                            self.workspace.root
                        )
                    ),
                    "copied": True,
                },
            )

        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=str(exc),
            )
