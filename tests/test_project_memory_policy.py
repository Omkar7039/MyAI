from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from project.project_memory import ProjectMemoryStore
from project.project_memory_policy import AutomaticProjectMemoryUpdater
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


def test_automatic_update_records_first_snapshot():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        store = ProjectMemoryStore(root / "project-memory.db")
        updater = AutomaticProjectMemoryUpdater(
            ProjectMemoryReconciler(store)
        )

        reconciliation, decision = updater.update(
            make_context(root, [("main.py", 100)])
        )

        assert reconciliation.stored is None
        assert decision.should_update is True
        assert len(store.history(root)) == 1


def test_automatic_update_skips_unchanged_project():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        store = ProjectMemoryStore(root / "project-memory.db")
        updater = AutomaticProjectMemoryUpdater(
            ProjectMemoryReconciler(store)
        )

        context = make_context(root, [("main.py", 100)])

        updater.update(context)
        reconciliation, decision = updater.update(context)

        assert reconciliation.stored is not None
        assert decision.should_update is False
        assert decision.reason == "Project state is unchanged."
        assert len(store.history(root)) == 1


def test_automatic_update_records_changed_project():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        store = ProjectMemoryStore(root / "project-memory.db")
        updater = AutomaticProjectMemoryUpdater(
            ProjectMemoryReconciler(store)
        )

        updater.update(
            make_context(root, [("main.py", 100)])
        )

        reconciliation, decision = updater.update(
            make_context(
                root,
                [
                    ("main.py", 150),
                    ("new.py", 50),
                ],
            )
        )

        assert reconciliation.stored is not None
        assert decision.should_update is True
        assert "changed" in decision.reason.lower()
        assert len(store.history(root)) == 2
