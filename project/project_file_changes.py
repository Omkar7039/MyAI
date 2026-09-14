from __future__ import annotations

from dataclasses import dataclass

from project.project_memory import ProjectSnapshot


@dataclass(frozen=True)
class ProjectFileChange:
    path: str
    status: str
    previous_size: int
    current_size: int


class ProjectFileChangeDetector:
    def compare(self, previous: ProjectSnapshot | None, current: ProjectSnapshot):
        previous_files = self._files(previous)
        current_files = self._files(current)
        changes = []

        for path in sorted(previous_files.keys() - current_files.keys()):
            changes.append(
                ProjectFileChange(
                    path=path,
                    status='deleted',
                    previous_size=previous_files[path],
                    current_size=0,
                )
            )

        for path in sorted(current_files.keys() - previous_files.keys()):
            changes.append(
                ProjectFileChange(
                    path=path,
                    status='added',
                    previous_size=0,
                    current_size=current_files[path],
                )
            )

        for path in sorted(previous_files.keys() & current_files.keys()):
            before = previous_files[path]
            after = current_files[path]

            if before != after:
                changes.append(
                    ProjectFileChange(
                        path=path,
                        status='modified',
                        previous_size=before,
                        current_size=after,
                    )
                )

        changes.sort(
            key=lambda item: (
                item.path,
                item.status,
            )
        )

        return changes

    @staticmethod
    def _files(snapshot: ProjectSnapshot | None):
        if snapshot is None:
            return {}
        return dict(snapshot.file_manifest)
