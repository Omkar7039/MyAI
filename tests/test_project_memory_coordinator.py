from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from project.project_memory import ProjectMemoryStore
from project.project_memory_coordinator import ProjectMemoryCoordinator
from project.project_state import ProjectStateManager


def make_context(root, files):
    infos = [SimpleNamespace(path=path, size=size, language="python") for path, size in files]
    return SimpleNamespace(
        root=str(root),
        repository_report=SimpleNamespace(files=infos, total_files=len(infos), total_bytes=sum(size for _, size in files)),
        code_index=SimpleNamespace(symbols=[]),
        dependency_graph=SimpleNamespace(nodes={}),
        call_graph=SimpleNamespace(nodes={}, edges=[]),
    )


def test_project_memory_coordinator_inspects_state():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        store = ProjectMemoryStore(root / "project-memory.db")
        manager = ProjectStateManager(store)
        coordinator = ProjectMemoryCoordinator(manager)

        manager.record(make_context(root, [("main.py", 100)]))

        context = coordinator.inspect(
            make_context(root, [("main.py", 150), ("new.py", 50)])
        )

        assert context.previous_snapshot is not None
        assert context.current_snapshot is not None
        assert context.changed_files == ("main.py", "new.py")


def test_project_memory_coordinator_inspect_and_record():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        store = ProjectMemoryStore(root / "project-memory.db")
        manager = ProjectStateManager(store)
        coordinator = ProjectMemoryCoordinator(manager)

        context = make_context(root, [("main.py", 100)])
        state, snapshot = coordinator.inspect_and_record(context)

        assert state.current_snapshot.fingerprint == snapshot.fingerprint
        assert state.previous_snapshot is None
        assert store.latest(root).fingerprint == snapshot.fingerprint


def test_project_memory_coordinator_respects_context_limit():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        coordinator = ProjectMemoryCoordinator(
            ProjectStateManager(ProjectMemoryStore(root / "project-memory.db"))
        )

        context = coordinator.inspect(
            make_context(root, [(f"file{i}.py", i + 100) for i in range(20)]),
            max_chars=100,
        )

        assert len(context.render()) <= 100
