from pathlib import Path
from tempfile import TemporaryDirectory

from project.project_retriever import ProjectRetriever


def test_read_changed_files_prioritizes_recent_changes():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'agents').mkdir()
        (root / 'utils').mkdir()

        (root / 'agents' / 'repair.py').write_text(
            'def repair():\n    return 1\n',
            encoding='utf-8',
        )
        (root / 'utils' / 'helpers.py').write_text(
            'def helper():\n    return 2\n',
            encoding='utf-8',
        )

        retriever = ProjectRetriever(root)

        evidence = retriever.read_changed_files(
            [
                'agents/repair.py',
                'utils/helpers.py',
            ],
            request='repair bug',
            changed_files=['utils/helpers.py'],
        )

        assert [item['file'] for item in evidence] == [
            'utils/helpers.py',
            'agents/repair.py',
        ]
        assert evidence[0]['score'] >= 100
        assert 'recently changed' in evidence[0]['reasons']


def test_read_changed_files_preserves_source_content():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'main.py').write_text(
            'def main():\n    return 42\n',
            encoding='utf-8',
        )

        retriever = ProjectRetriever(root)
        evidence = retriever.read_changed_files(
            ['main.py'],
            request='main function',
            changed_files=['main.py'],
        )

        assert len(evidence) == 1
        assert evidence[0]['source'] == 'def main():\n    return 42\n'
        assert evidence[0]['score'] >= 100
