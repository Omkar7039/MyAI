from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from project.project_memory import ProjectMemoryStore
from project.project_state import ProjectStateManager


def make_context(root, file_specs):
    files = [
        SimpleNamespace(
            path=path,
            size=size,
            language='python',
        )
        for path, size in file_specs
    ]

    report = SimpleNamespace(
        files=files,
        total_files=len(files),
        total_bytes=sum(size for _, size in file_specs),
    )

    code_index = SimpleNamespace(
        symbols=[],
    )

    dependency_graph = SimpleNamespace(
        nodes={},
    )

    call_graph = SimpleNamespace(
        nodes={},
        edges=[],
    )

    return SimpleNamespace(
        root=str(root),
        repository_report=report,
        code_index=code_index,
        dependency_graph=dependency_graph,
        call_graph=call_graph,
    )


def test_project_state_manager_reports_first_snapshot():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        store = ProjectMemoryStore(root / 'project-memory.db')
        manager = ProjectStateManager(store)

        context = make_context(
            root,
            [('main.py', 100), ('utils.py', 200)],
        )

        state = manager.summarize(context)

        assert state.previous is None
        assert state.structural.changed is True
        assert state.added_files == ('main.py', 'utils.py')
        assert state.modified_files == ()
        assert state.deleted_files == ()
        assert 'Added files: 2' in state.render()


def test_project_state_manager_compares_against_recorded_history():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        store = ProjectMemoryStore(root / 'project-memory.db')
        manager = ProjectStateManager(store)

        first_context = make_context(
            root,
            [('main.py', 100), ('utils.py', 200)],
        )
        second_context = make_context(
            root,
            [('main.py', 150), ('new.py', 75)],
        )

        manager.record(first_context)
        state = manager.summarize(second_context)

        assert state.previous is not None
        assert state.added_files == ('new.py',)
        assert state.modified_files == ('main.py',)
        assert state.deleted_files == ('utils.py',)
        assert state.changed_files == (
            'main.py',
            'new.py',
            'utils.py',
        )
        assert 'Modified: main.py' in state.render()
        assert 'Added: new.py' in state.render()
        assert 'Deleted: utils.py' in state.render()


def test_project_state_manager_record_persists_latest_snapshot():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        store = ProjectMemoryStore(root / 'project-memory.db')
        manager = ProjectStateManager(store)

        context = make_context(
            root,
            [('main.py', 100)],
        )

        snapshot = manager.record(context)
        latest = store.latest(root)

        assert latest is not None
        assert latest.fingerprint == snapshot.fingerprint
        assert latest.file_manifest == (('main.py', 100),)
