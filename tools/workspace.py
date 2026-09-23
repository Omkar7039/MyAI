from __future__ import annotations

from pathlib import Path


class Workspace:
    """
    Defines and enforces the filesystem boundary for MyAI tools.
    """

    def __init__(
        self,
        root: str | Path | None = None,
    ):
        self.root = (
            Path(root).expanduser().resolve()
            if root is not None
            else Path.cwd().resolve()
        )

    def resolve(
        self,
        path: str | Path = ".",
    ) -> Path:
        requested = Path(path).expanduser()

        if not requested.is_absolute():
            requested = self.root / requested

        resolved = requested.resolve()

        try:
            resolved.relative_to(self.root)
        except ValueError:
            raise ValueError(
                "Path is outside the allowed workspace."
            )

        return resolved

    def exists(
        self,
        path: str | Path,
    ) -> bool:
        return self.resolve(path).exists()

    def is_file(
        self,
        path: str | Path,
    ) -> bool:
        return self.resolve(path).is_file()

    def is_directory(
        self,
        path: str | Path,
    ) -> bool:
        return self.resolve(path).is_dir()
