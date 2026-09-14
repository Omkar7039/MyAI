from __future__ import annotations

from dataclasses import dataclass

from project.project_memory import ProjectMemoryStore


@dataclass(frozen=True)
class ProjectMemoryHealth:
    healthy: bool
    snapshot_count: int
    latest_available: bool
    manifests_valid: bool
    message: str


class ProjectMemoryHealthChecker:
    def __init__(self, store: ProjectMemoryStore | None = None):
        self.store = store or ProjectMemoryStore()

    def check(self, project_root: str) -> ProjectMemoryHealth:
        try:
            history = self.store.history(project_root, limit=1000)
        except Exception as exc:
            return ProjectMemoryHealth(
                healthy=False,
                snapshot_count=0,
                latest_available=False,
                manifests_valid=False,
                message=f"Project memory read failed: {exc}",
            )

        latest = self.store.latest(project_root)
        manifests_valid = all(
            isinstance(snapshot.file_manifest, tuple)
            and all(
                isinstance(path, str)
                and isinstance(size, int)
                and size >= 0
                for path, size in snapshot.file_manifest
            )
            for snapshot in history
        )

        healthy = (
            latest is not None
            and manifests_valid
        )

        if healthy:
            message = "Project memory is healthy."
        elif not history:
            message = "Project memory has no stored snapshots."
        else:
            message = "Project memory integrity check failed."

        return ProjectMemoryHealth(
            healthy=healthy,
            snapshot_count=len(history),
            latest_available=latest is not None,
            manifests_valid=manifests_valid,
            message=message,
        )
