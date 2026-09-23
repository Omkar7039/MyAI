from __future__ import annotations

from pathlib import Path

from tools.base import ToolResult
from tools.workspace import Workspace


class DirectoryTreeTool:
    """
    Return a structured directory tree inside the allowed workspace.
    """

    name = "directory_tree"

    description = (
        "Inspect a local directory as a structured tree inside the allowed workspace."
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
        max_depth: int = 3,
    ) -> ToolResult:
        try:
            if not path.strip():
                raise ValueError("No directory path supplied.")

            if isinstance(max_depth, bool) or not isinstance(max_depth, int):
                raise ValueError("max_depth must be an integer.")

            if max_depth < 0:
                raise ValueError("max_depth must be zero or greater.")

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

            root_relative = str(
                resolved.relative_to(self.workspace.root)
            )

            entries = []

            def walk(directory: Path, depth: int) -> None:
                children = sorted(
                    directory.iterdir(),
                    key=lambda item: (
                        not item.is_dir(),
                        item.name.lower(),
                    ),
                )

                for child in children:
                    relative_path = str(
                        child.relative_to(self.workspace.root)
                    )

                    if child.is_dir():
                        entries.append(
                            {
                                "path": relative_path,
                                "name": child.name,
                                "type": "directory",
                                "depth": depth + 1,
                            }
                        )

                        if depth < max_depth:
                            walk(child, depth + 1)
                    else:
                        entries.append(
                            {
                                "path": relative_path,
                                "name": child.name,
                                "type": "file",
                                "depth": depth + 1,
                            }
                        )

            walk(resolved, 0)

            return ToolResult(
                tool_name=self.name,
                success=True,
                result={
                    "path": root_relative,
                    "max_depth": max_depth,
                    "entries": entries,
                },
            )

        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=str(exc),
            )
