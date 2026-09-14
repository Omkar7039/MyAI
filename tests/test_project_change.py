from pathlib import Path
from types import SimpleNamespace

from project.project_change import ProjectChangeDetector
from project.project_memory import ProjectSnapshotBuilder


def make_context(root, files=2, total_bytes=300, symbols=2, dep_edges=1, call_edges=1):
    file_items = [
        SimpleNamespace(path=f'file{i}.py', size=100, language='python')
        for i in range(files)
    ]

    report = SimpleNamespace(
        files=file_items,
        total_files=files,
        total_bytes=total_bytes,
    )

    code_index = SimpleNamespace(
        symbols=[SimpleNamespace(name=f's{i}') for i in range(symbols)]
    )

    imports = {'utils.py'} if dep_edges else set()
    dependency_graph = SimpleNamespace(
        nodes={
            'main.py': SimpleNamespace(imports=imports),
            'utils.py': SimpleNamespace(imports=set()),
        }
    )

    edges = [
        SimpleNamespace(caller=f'c{i}', callee=f'd{i}')
        for i in range(call_edges)
    ]
    call_graph = SimpleNamespace(
        nodes={f'n{i}': object() for i in range(max(call_edges + 1, 2))},
        edges=edges,
    )

    return SimpleNamespace(
        root=str(root),
        repository_report=report,
        code_index=code_index,
        dependency_graph=dependency_graph,
        call_graph=call_graph,
    )


def test_project_change_detector_reports_no_change():
    root = Path('/tmp/myai-project')
    context = make_context(root)

    previous = ProjectSnapshotBuilder.build(
        context,
        created_at='2026-01-01T00:00:00+00:00',
    )
    current = ProjectSnapshotBuilder.build(
        context,
        created_at='2026-02-01T00:00:00+00:00',
    )

    report = ProjectChangeDetector().compare(previous, current)

    assert report.changed is False
    assert report.fingerprint_changed is False
    assert report.files_delta == 0
    assert report.symbols_delta == 0
    assert report.summary == 'Project unchanged since previous snapshot.'


def test_project_change_detector_reports_structural_changes():
    root = Path('/tmp/myai-project')

    previous_context = make_context(root)
    current_context = make_context(
        root,
        files=3,
        total_bytes=450,
        symbols=4,
        dep_edges=1,
        call_edges=2,
    )

    previous = ProjectSnapshotBuilder.build(previous_context)
    current = ProjectSnapshotBuilder.build(current_context)

    report = ProjectChangeDetector().compare(previous, current)

    assert report.changed is True
    assert report.fingerprint_changed is True
    assert report.files_delta == 1
    assert report.bytes_delta == 150
    assert report.symbols_delta == 2
    assert report.call_edges_delta == 1
    assert 'Project changed:' in report.summary
    assert 'files +1' in report.summary
    assert 'symbols +2' in report.summary


def test_project_change_detector_handles_missing_history():
    root = Path('/tmp/myai-project')
    current = ProjectSnapshotBuilder.build(
        make_context(root),
        created_at='2026-03-01T00:00:00+00:00',
    )

    report = ProjectChangeDetector().compare(None, current)

    assert report.changed is True
    assert report.fingerprint_changed is True
    assert report.files_delta == current.total_files
    assert report.symbols_delta == current.symbol_count
