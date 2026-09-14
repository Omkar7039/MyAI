from __future__ import annotations

from dataclasses import dataclass

from project.project_change import ProjectChangeDetector, ProjectChangeReport
from project.project_file_changes import ProjectFileChange, ProjectFileChangeDetector
from project.project_memory import ProjectMemoryStore, ProjectSnapshot


@dataclass(frozen=True)
class ProjectHistoryEntry:
    current: ProjectSnapshot
    previous: ProjectSnapshot | None
    structural: ProjectChangeReport
    files: tuple[ProjectFileChange, ...]

    @property
    def changed(self) -> bool:
        return self.structural.changed


class ProjectHistoryQuery:
    def __init__(self, store: ProjectMemoryStore | None = None):
        self.store = store or ProjectMemoryStore()
        self.change_detector = ProjectChangeDetector()
        self.file_change_detector = ProjectFileChangeDetector()

    def latest(self, project_root: str, limit: int = 20):
        if limit < 1:
            raise ValueError("limit must be >= 1")

        snapshots = list(self.store.history(project_root, limit=limit))

        entries = []

        for index, current in enumerate(snapshots):
            previous = snapshots[index + 1] if index + 1 < len(snapshots) else None

            structural = self.change_detector.compare(
                previous,
                current,
            )

            files = tuple(
                self.file_change_detector.compare(
                    previous,
                    current,
                )
            )

            entries.append(
                ProjectHistoryEntry(
                    current=current,
                    previous=previous,
                    structural=structural,
                    files=files,
                )
            )

        return entries

    def changed_since(
        self,
        project_root: str,
        fingerprint: str,
    ):
        history = list(self.store.history(project_root, limit=1000))

        index = None

        for position, snapshot in enumerate(history):
            if snapshot.fingerprint == fingerprint:
                index = position
                break

        if index is None:
            return ()

        newer_snapshots = list(reversed(history[:index]))

        entries = []

        for position, current in enumerate(newer_snapshots):
            previous = (
                newer_snapshots[position + 1]
                if position + 1 < len(newer_snapshots)
                else None
            )

            structural = self.change_detector.compare(
                previous,
                current,
            )

            files = tuple(
                self.file_change_detector.compare(
                    previous,
                    current,
                )
            )

            entries.append(
                ProjectHistoryEntry(
                    current=current,
                    previous=previous,
                    structural=structural,
                    files=files,
                )
            )

        return tuple(entries)
