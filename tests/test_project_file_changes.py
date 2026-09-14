from types import SimpleNamespace
from pathlib import Path

from project.project_file_changes import ProjectFileChangeDetector
from project.project_memory import ProjectSnapshotBuilder


def make_context(root, file_specs):
    files = [
        SimpleNamespace(path=path, size=size, language='python')
        for path, size in file_specs
    ]

    report = SimpleNamespace(
        files=files,
        total_files=len(files),
        total_bytes=sum(size for _, size in file_specs),
    )

    code_index = SimpleNamespace(symbols=[])
    dependency_graph = SimpleNamespace(nodes={})
    call_graph = SimpleNamespace(nodes={}, edges=[])

    return SimpleNamespace(
        root=str(root),
        repository_report=report,
        code_index=code_index,
        dependency_graph=dependency_graph,
        call_graph=call_graph,
    )


def test_project_file_changes_detects_added_modified_deleted():
    root = Path('/tmp/myai-project')

    previous = ProjectSnapshotBuilder.build(
        make_context(
            root,
            [('same.py', 100), ('modified.py', 100), ('deleted.py', 80)],
        )
    )

    current = ProjectSnapshotBuilder.build(
        make_context(
            root,
            [('same.py', 100), ('modified.py', 150), ('added.py', 60)],
        )
    )

    changes = ProjectFileChangeDetector().compare(previous, current)

    assert [(item.path, item.status) for item in changes] == [
        ('added.py', 'added'),
        ('deleted.py', 'deleted'),
        ('modified.py', 'modified'),
    ]

    modified = changes[2]
    assert modified.previous_size == 100
    assert modified.current_size == 150


def test_project_file_changes_handles_first_snapshot():
    root = Path('/tmp/myai-project')

    current = ProjectSnapshotBuilder.build(
        make_context(root, [('main.py', 100), ('utils.py', 200)])
    )

    changes = ProjectFileChangeDetector().compare(None, current)

    assert [(item.path, item.status) for item in changes] == [
        ('main.py', 'added'),
        ('utils.py', 'added'),
    ]
