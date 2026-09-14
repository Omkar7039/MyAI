from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from project.project_memory import ProjectMemoryStore, ProjectSnapshotBuilder
from project.project_memory_health import ProjectMemoryHealthChecker


def make_context(root):
    files = [
        SimpleNamespace(
            path="main.py",
            size=100,
            language="python",
        ),
    ]

    return SimpleNamespace(
        root=str(root),
        repository_report=SimpleNamespace(
            files=files,
            total_files=1,
            total_bytes=100,
        ),
        code_index=SimpleNamespace(symbols=[]),
        dependency_graph=SimpleNamespace(nodes={}),
        call_graph=SimpleNamespace(nodes={}, edges=[]),
    )


def test_empty_project_memory_is_reported_as_empty():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        store = ProjectMemoryStore(root / "project-memory.db")
        health = ProjectMemoryHealthChecker(store).check(str(root))

        assert health.healthy is False
        assert health.snapshot_count == 0
        assert health.latest_available is False
        assert health.message == "Project memory has no stored snapshots."


def test_valid_project_memory_is_healthy():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        store = ProjectMemoryStore(root / "project-memory.db")

        snapshot = ProjectSnapshotBuilder.build(
            make_context(root),
            created_at="2026-01-01T00:00:00+00:00",
        )
        store.save(snapshot)

        health = ProjectMemoryHealthChecker(store).check(str(root))

        assert health.healthy is True
        assert health.snapshot_count == 1
        assert health.latest_available is True
        assert health.manifests_valid is True
        assert health.message == "Project memory is healthy."


def test_multiple_valid_snapshots_remain_healthy():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        store = ProjectMemoryStore(root / "project-memory.db")

        first = ProjectSnapshotBuilder.build(
            make_context(root),
            created_at="2026-01-01T00:00:00+00:00",
        )
        second = ProjectSnapshotBuilder.build(
            make_context(root),
            created_at="2026-02-01T00:00:00+00:00",
        )

        store.save(first)
        store.save(second)

        health = ProjectMemoryHealthChecker(store).check(str(root))

        assert health.healthy is True
        assert health.snapshot_count == 2
        assert health.latest_available is True
        assert health.manifests_valid is True
