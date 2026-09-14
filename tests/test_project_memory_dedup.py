from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from project.project_memory import ProjectMemoryStore
from project.project_memory_dedup import ProjectMemoryDeduplicator


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


def test_identical_snapshot_is_not_saved_twice():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        store = ProjectMemoryStore(root / "project-memory.db")
        dedup = ProjectMemoryDeduplicator(store)

        context = make_context(
            root,
            [("main.py", 100)],
        )

        first = dedup.save_if_changed(context)
        second = dedup.save_if_changed(context)

        assert first.saved is True
        assert second.saved is False
        assert "identical" in second.reason.lower()
        assert len(store.history(root)) == 1


def test_changed_snapshot_is_saved():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        store = ProjectMemoryStore(root / "project-memory.db")
        dedup = ProjectMemoryDeduplicator(store)

        first = dedup.save_if_changed(
            make_context(
                root,
                [("main.py", 100)],
            )
        )

        second = dedup.save_if_changed(
            make_context(
                root,
                [("main.py", 150)],
            )
        )

        assert first.saved is True
        assert second.saved is True
        assert first.snapshot.fingerprint != second.snapshot.fingerprint
        assert len(store.history(root)) == 2


def test_deduplication_is_scoped_to_each_project():
    with TemporaryDirectory() as tmp:
        base = Path(tmp).resolve()
        project_a = base / "a"
        project_b = base / "b"

        project_a.mkdir()
        project_b.mkdir()

        store = ProjectMemoryStore(base / "project-memory.db")
        dedup = ProjectMemoryDeduplicator(store)

        first = dedup.save_if_changed(
            make_context(
                project_a,
                [("main.py", 100)],
            )
        )

        second = dedup.save_if_changed(
            make_context(
                project_b,
                [("main.py", 100)],
            )
        )

        assert first.saved is True
        assert second.saved is True
        assert len(store.history(project_a)) == 1
        assert len(store.history(project_b)) == 1
