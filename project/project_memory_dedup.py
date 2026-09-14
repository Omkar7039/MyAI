from __future__ import annotations

from dataclasses import dataclass

from project.project_memory import ProjectMemoryStore, ProjectSnapshot, ProjectSnapshotBuilder


@dataclass(frozen=True)
class SnapshotSaveResult:
    snapshot: ProjectSnapshot
    saved: bool
    reason: str


class ProjectMemoryDeduplicator:
    def __init__(self, store: ProjectMemoryStore | None = None):
        self.store = store or ProjectMemoryStore()

    def save_if_changed(self, context) -> SnapshotSaveResult:
        snapshot = ProjectSnapshotBuilder.build(context)
        latest = self.store.latest(snapshot.project_root)

        if latest is not None and latest.fingerprint == snapshot.fingerprint:
            return SnapshotSaveResult(
                snapshot=snapshot,
                saved=False,
                reason="Project snapshot is identical to the latest stored state.",
            )

        self.store.save(snapshot)

        return SnapshotSaveResult(
            snapshot=snapshot,
            saved=True,
            reason="Project snapshot stored as a new state.",
        )
