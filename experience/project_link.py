from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExperienceProjectLink:
    experience_id: str
    project_root: str
    file_paths: tuple[str, ...] = ()
    symbols: tuple[str, ...] = ()
    commit_id: str = ""


class ExperienceProjectLinker:
    """Associate historical experiences with project-level context."""

    def link(
        self,
        experience_id: str,
        project_root: str,
        file_paths: tuple[str, ...] = (),
        symbols: tuple[str, ...] = (),
        commit_id: str = "",
    ) -> ExperienceProjectLink:
        experience_id = experience_id.strip()
        project_root = project_root.strip()

        if not experience_id:
            raise ValueError("experience_id must not be empty")
        if not project_root:
            raise ValueError("project_root must not be empty")

        clean_files = tuple(
            path.strip()
            for path in file_paths
            if path and path.strip()
        )

        clean_symbols = tuple(
            symbol.strip()
            for symbol in symbols
            if symbol and symbol.strip()
        )

        return ExperienceProjectLink(
            experience_id=experience_id,
            project_root=project_root,
            file_paths=clean_files,
            symbols=clean_symbols,
            commit_id=commit_id.strip(),
        )
