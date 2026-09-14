from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory

from project.project_memory import ProjectMemoryStore, ProjectSnapshotBuilder


def make_context(root):
    files = [
        SimpleNamespace(path='main.py', size=100, language='python'),
        SimpleNamespace(path='utils.py', size=200, language='python'),
    ]

    report = SimpleNamespace(
        files=files,
        total_files=2,
        total_bytes=300,
    )

    symbols = [
        SimpleNamespace(name='main'),
        SimpleNamespace(name='helper'),
    ]

    code_index = SimpleNamespace(symbols=symbols)

    dependency_graph = SimpleNamespace(
        nodes={
            'main.py': SimpleNamespace(imports={'utils.py'}),
            'utils.py': SimpleNamespace(imports=set()),
        }
    )

    call_graph = SimpleNamespace(
        nodes={'main': object(), 'helper': object()},
        edges=[SimpleNamespace(caller='main', callee='helper')],
    )

    return SimpleNamespace(
        root=str(root),
        repository_report=report,
        code_index=code_index,
        dependency_graph=dependency_graph,
        call_graph=call_graph,
    )


def test_project_snapshot_builds_deterministic_identity():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        context = make_context(root)

        first = ProjectSnapshotBuilder.build(
            context,
            created_at='2026-01-01T00:00:00+00:00',
        )
        second = ProjectSnapshotBuilder.build(
            context,
            created_at='2026-02-01T00:00:00+00:00',
        )

        assert first.project_root == str(root)
        assert first.fingerprint == second.fingerprint
        assert first.total_files == 2
        assert first.total_bytes == 300
        assert first.symbol_count == 2
        assert first.dependency_nodes == 2
        assert first.dependency_edges == 1
        assert first.call_nodes == 2
        assert first.call_edges == 1


def test_project_snapshot_persists_and_returns_latest_history():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        store = ProjectMemoryStore(root / 'project-memory.db')
        context = make_context(root)

        first = ProjectSnapshotBuilder.build(
            context,
            created_at='2026-01-01T00:00:00+00:00',
        )
        second = ProjectSnapshotBuilder.build(
            context,
            created_at='2026-02-01T00:00:00+00:00',
        )

        first_id = store.save(first)
        second_id = store.save(second)

        assert second_id > first_id
        assert store.latest(root).created_at == second.created_at

        history = store.history(root, limit=10)
        assert len(history) == 2
        assert history[0].created_at == second.created_at
        assert history[1].created_at == first.created_at


def test_project_snapshot_history_is_scoped_to_project():
    with TemporaryDirectory() as tmp:
        base = Path(tmp).resolve()
        project_a = base / 'a'
        project_b = base / 'b'
        project_a.mkdir()
        project_b.mkdir()

        store = ProjectMemoryStore(base / 'project-memory.db')

        store.save(
            ProjectSnapshotBuilder.build(
                make_context(project_a),
                created_at='2026-01-01T00:00:00+00:00',
            )
        )
        store.save(
            ProjectSnapshotBuilder.build(
                make_context(project_b),
                created_at='2026-01-02T00:00:00+00:00',
            )
        )

        history_a = store.history(project_a)
        history_b = store.history(project_b)

        assert len(history_a) == 1
        assert len(history_b) == 1
        assert history_a[0].project_root == str(project_a)
        assert history_b[0].project_root == str(project_b)
