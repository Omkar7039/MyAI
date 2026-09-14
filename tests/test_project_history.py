from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from project.project_history import ProjectHistoryQuery
from project.project_memory import ProjectMemoryStore, ProjectSnapshotBuilder


def make_context(root, files):
    infos = [
        SimpleNamespace(
            path=path,
            size=size,
            language="python",
        )
        for path, size in files
    ]

    return SimpleNamespace(
        root=str(root),
        repository_report=SimpleNamespace(
            files=infos,
            total_files=len(infos),
            total_bytes=sum(size for _, size in files),
        ),
        code_index=SimpleNamespace(symbols=[]),
        dependency_graph=SimpleNamespace(nodes={}),
        call_graph=SimpleNamespace(nodes={}, edges=[]),
    )


def test_history_query_returns_newest_first():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        store = ProjectMemoryStore(root / "project-memory.db")

        snapshots = [
            ProjectSnapshotBuilder.build(
                make_context(root, [("main.py", 100)]),
                created_at="2026-01-01T00:00:00+00:00",
            ),
            ProjectSnapshotBuilder.build(
                make_context(root, [("main.py", 150)]),
                created_at="2026-02-01T00:00:00+00:00",
            ),
            ProjectSnapshotBuilder.build(
                make_context(
                    root,
                    [("main.py", 150), ("new.py", 50)],
                ),
                created_at="2026-03-01T00:00:00+00:00",
            ),
        ]

        for snapshot in snapshots:
            store.save(snapshot)

        history = ProjectHistoryQuery(store).latest(str(root))

        assert len(history) == 3
        assert history[0].current.created_at == "2026-03-01T00:00:00+00:00"
        assert history[1].current.created_at == "2026-02-01T00:00:00+00:00"
        assert history[2].current.created_at == "2026-01-01T00:00:00+00:00"


def test_history_query_detects_changes_between_snapshots():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        store = ProjectMemoryStore(root / "project-memory.db")

        first = ProjectSnapshotBuilder.build(
            make_context(root, [("main.py", 100)]),
            created_at="2026-01-01T00:00:00+00:00",
        )
        second = ProjectSnapshotBuilder.build(
            make_context(
                root,
                [("main.py", 150), ("new.py", 50)],
            ),
            created_at="2026-02-01T00:00:00+00:00",
        )

        store.save(first)
        store.save(second)

        history = ProjectHistoryQuery(store).latest(str(root))
        newest = history[0]

        assert newest.previous is not None
        assert newest.changed is True
        assert {item.path for item in newest.files} == {
            "main.py",
            "new.py",
        }


def test_history_query_can_find_changes_since_fingerprint():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        store = ProjectMemoryStore(root / "project-memory.db")

        first = ProjectSnapshotBuilder.build(
            make_context(root, [("main.py", 100)]),
            created_at="2026-01-01T00:00:00+00:00",
        )
        second = ProjectSnapshotBuilder.build(
            make_context(root, [("main.py", 150)]),
            created_at="2026-02-01T00:00:00+00:00",
        )
        third = ProjectSnapshotBuilder.build(
            make_context(
                root,
                [("main.py", 150), ("new.py", 50)],
            ),
            created_at="2026-03-01T00:00:00+00:00",
        )

        for snapshot in (first, second, third):
            store.save(snapshot)

        changes = ProjectHistoryQuery(store).changed_since(
            str(root),
            first.fingerprint,
        )

        assert len(changes) == 2
        assert changes[0].current.fingerprint == second.fingerprint
        assert changes[1].current.fingerprint == third.fingerprint
