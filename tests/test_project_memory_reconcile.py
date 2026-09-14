from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from project.project_memory import ProjectMemoryStore
from project.project_memory_reconcile import ProjectMemoryReconciler


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


def test_reconciliation_detects_missing_project_snapshot():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        store = ProjectMemoryStore(root / "project-memory.db")
        reconciler = ProjectMemoryReconciler(store)

        result = reconciler.inspect(
            make_context(root, [("main.py", 100)])
        )

        assert result.stored is None
        assert result.needs_update is True
        assert result.current.total_files == 1
        assert result.changed_files == ()


def test_reconciliation_detects_live_project_changes():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        store = ProjectMemoryStore(root / "project-memory.db")
        reconciler = ProjectMemoryReconciler(store)

        initial = make_context(
            root,
            [("main.py", 100)],
        )
        changed = make_context(
            root,
            [("main.py", 150), ("new.py", 50)],
        )

        reconciler.reconcile(initial)

        result = reconciler.inspect(changed)

        assert result.stored is not None
        assert result.needs_update is True
        assert {item.path for item in result.changed_files} == {
            "main.py",
            "new.py",
        }


def test_reconcile_updates_stored_snapshot_when_needed():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        store = ProjectMemoryStore(root / "project-memory.db")
        reconciler = ProjectMemoryReconciler(store)

        initial = make_context(
            root,
            [("main.py", 100)],
        )
        changed = make_context(
            root,
            [("main.py", 150)],
        )

        first = reconciler.reconcile(initial)
        second = reconciler.reconcile(changed)

        assert first.needs_update is True
        assert second.needs_update is True
        assert store.latest(root).fingerprint == second.current.fingerprint
        assert len(store.history(root)) == 2
