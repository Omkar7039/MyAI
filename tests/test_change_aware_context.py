from pathlib import Path
from tempfile import TemporaryDirectory

from project.change_aware_context import ChangeAwareContextAssembler
from project.project_retriever import ProjectRetriever


def test_change_aware_context_prioritizes_changed_source():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)

        (root / "repair.py").write_text(
            "def repair():\n    return 1\n",
            encoding="utf-8",
        )
        (root / "utils.py").write_text(
            "def helper():\n    return 2\n",
            encoding="utf-8",
        )

        assembler = ChangeAwareContextAssembler(
            ProjectRetriever(root)
        )

        context = assembler.assemble(
            ["repair.py", "utils.py"],
            request="helper bug",
            changed_files=["utils.py"],
        )

        assert context.changed_files == ("utils.py",)
        assert context.files[0]["file"] == "utils.py"
        assert "FILE: utils.py" in context.text
        assert "def helper():" in context.text


def test_change_aware_context_is_bounded():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)

        for index in range(10):
            (root / f"file{index}.py").write_text(
                "def example():\n" + ("    return 42\n" * 20),
                encoding="utf-8",
            )

        assembler = ChangeAwareContextAssembler(
            ProjectRetriever(root)
        )

        context = assembler.assemble(
            [f"file{index}.py" for index in range(10)],
            request="example",
            changed_files=["file9.py"],
            max_chars=500,
        )

        assert len(context.text) <= 500


def test_change_aware_context_rejects_invalid_limit():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        assembler = ChangeAwareContextAssembler(
            ProjectRetriever(root)
        )

        try:
            assembler.assemble(
                ["main.py"],
                request="main",
                max_chars=0,
            )
        except ValueError as exc:
            assert str(exc) == "max_chars must be >= 1"
        else:
            raise AssertionError("Expected ValueError")
