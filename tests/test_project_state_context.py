from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from project.project_memory import ProjectMemoryStore
from project.project_state import ProjectStateManager
from project.project_state_context import ProjectStateContextBuilder


def make_context(root, files):
    infos = [
        SimpleNamespace(
            path=path,
            size=size,
            language='python',
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


def test_unified_project_state_context_exposes_changes():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        store = ProjectMemoryStore(root / 'project-memory.db')
        manager = ProjectStateManager(store)
        builder = ProjectStateContextBuilder(manager)

        manager.record(
            make_context(root, [('main.py', 100)])
        )

        context = builder.build(
            make_context(
                root,
                [('main.py', 150), ('new.py', 50)],
            )
        )

        assert context.current_snapshot is not None
        assert context.previous_snapshot is not None
        assert context.changed_files == ('main.py', 'new.py')
        assert 'Modified: main.py' in context.render()
        assert 'Added: new.py' in context.render()


def test_unified_project_state_context_is_bounded():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        manager = ProjectStateManager(
            ProjectMemoryStore(root / 'project-memory.db')
        )
        builder = ProjectStateContextBuilder(manager)

        context = builder.build(
            make_context(
                root,
                [(f'file{i}.py', i + 100) for i in range(20)],
            ),
            max_chars=120,
        )

        assert len(context.render()) <= 120


def test_unified_project_state_context_rejects_invalid_limit():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        builder = ProjectStateContextBuilder(
            ProjectStateManager(
                ProjectMemoryStore(root / 'project-memory.db')
            )
        )

        try:
            builder.build(
                make_context(root, [('main.py', 100)]),
                max_chars=0,
            )
        except ValueError as exc:
            assert str(exc) == 'max_chars must be >= 1'
        else:
            raise AssertionError('Expected ValueError')
