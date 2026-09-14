from __future__ import annotations

from dataclasses import dataclass

from project.project_change import ProjectChangeDetector, ProjectChangeReport
from project.project_file_changes import ProjectFileChange, ProjectFileChangeDetector
from project.project_memory import ProjectMemoryStore, ProjectSnapshot, ProjectSnapshotBuilder


@dataclass(frozen=True)
class ProjectStateSummary:
    previous: ProjectSnapshot | None
    current: ProjectSnapshot
    structural: ProjectChangeReport
    files: tuple[ProjectFileChange, ...]

    @property
    def changed_files(self) -> tuple[str, ...]:
        return tuple(change.path for change in self.files)

    @property
    def added_files(self) -> tuple[str, ...]:
        return tuple(
            change.path
            for change in self.files
            if change.status == 'added'
        )

    @property
    def modified_files(self) -> tuple[str, ...]:
        return tuple(
            change.path
            for change in self.files
            if change.status == 'modified'
        )

    @property
    def deleted_files(self) -> tuple[str, ...]:
        return tuple(
            change.path
            for change in self.files
            if change.status == 'deleted'
        )

    def render(self) -> str:
        lines = [
            self.structural.summary,
            '',
            f'Added files: {len(self.added_files)}',
            f'Modified files: {len(self.modified_files)}',
            f'Deleted files: {len(self.deleted_files)}',
        ]

        if self.added_files:
            lines.append('Added: ' + ', '.join(self.added_files))
        if self.modified_files:
            lines.append('Modified: ' + ', '.join(self.modified_files))
        if self.deleted_files:
            lines.append('Deleted: ' + ', '.join(self.deleted_files))

        return '\n'.join(lines)


class ProjectStateManager:
    def __init__(self, store: ProjectMemoryStore | None = None):
        self.store = store or ProjectMemoryStore()
        self.change_detector = ProjectChangeDetector()
        self.file_change_detector = ProjectFileChangeDetector()

    def summarize(self, context) -> ProjectStateSummary:
        current = ProjectSnapshotBuilder.build(context)
        previous = self.store.latest(current.project_root)

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

        return ProjectStateSummary(
            previous=previous,
            current=current,
            structural=structural,
            files=files,
        )

    def record(self, context) -> ProjectSnapshot:
        snapshot = ProjectSnapshotBuilder.build(context)
        self.store.save(snapshot)
        return snapshot
