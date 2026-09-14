from __future__ import annotations

from dataclasses import dataclass

from project.project_change import ProjectChangeDetector, ProjectChangeReport
from project.project_file_changes import ProjectFileChange
from project.project_memory import (
    ProjectMemoryStore,
    ProjectSnapshot,
    ProjectSnapshotBuilder,
)


@dataclass(frozen=True)
class ProjectReconciliation:
    stored: ProjectSnapshot | None
    current: ProjectSnapshot
    changes: ProjectChangeReport
    changed_files: tuple[ProjectFileChange, ...]

    @property
    def needs_update(self) -> bool:
        return self.stored is None or self.changes.changed


class ProjectMemoryReconciler:
    def __init__(self, store: ProjectMemoryStore | None = None):
        self.store = store or ProjectMemoryStore()
        self.change_detector = ProjectChangeDetector()

    def inspect(self, context) -> ProjectReconciliation:
        current = ProjectSnapshotBuilder.build(context)
        stored = self.store.latest(current.project_root)

        changes = self.change_detector.compare(
            stored,
            current,
        )

        if stored is None:
            changed_files = ()
        else:
            from project.project_file_changes import ProjectFileChangeDetector

            changed_files = tuple(
                ProjectFileChangeDetector().compare(
                    stored,
                    current,
                )
            )

        return ProjectReconciliation(
            stored=stored,
            current=current,
            changes=changes,
            changed_files=changed_files,
        )

    def reconcile(self, context) -> ProjectReconciliation:
        result = self.inspect(context)

        if result.needs_update:
            self.store.save(result.current)

        return result
