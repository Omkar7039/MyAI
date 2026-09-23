from pathlib import Path

from tools.edit_file_tool import EditFileTool
from tools.workspace import Workspace


def test_edit_file_replaces_exact_text(tmp_path: Path):
    target = tmp_path / "example.py"

    target.write_text(
        "value = 10\nprint(value)\n",
        encoding="utf-8",
    )

    tool = EditFileTool(tmp_path)

    result = tool.execute(
        "example.py",
        "value = 10",
        "value = 20",
    )

    assert result.success is True
    assert result.result["path"] == "example.py"
    assert result.result["replacements"] == 1

    assert target.read_text(
        encoding="utf-8"
    ) == "value = 20\nprint(value)\n"


def test_edit_file_rejects_missing_file(tmp_path: Path):
    tool = EditFileTool(tmp_path)

    result = tool.execute(
        "missing.py",
        "old",
        "new",
    )

    assert result.success is False
    assert "File does not exist" in result.error


def test_edit_file_rejects_missing_old_text(tmp_path: Path):
    target = tmp_path / "example.txt"

    target.write_text(
        "hello world",
        encoding="utf-8",
    )

    tool = EditFileTool(tmp_path)

    result = tool.execute(
        "example.txt",
        "missing",
        "new",
    )

    assert result.success is False
    assert "old text was not found" in result.error


def test_edit_file_rejects_ambiguous_old_text(tmp_path: Path):
    target = tmp_path / "example.txt"

    target.write_text(
        "hello\nhello\n",
        encoding="utf-8",
    )

    tool = EditFileTool(tmp_path)

    result = tool.execute(
        "example.txt",
        "hello",
        "goodbye",
    )

    assert result.success is False
    assert "occurs multiple times" in result.error

    assert target.read_text(
        encoding="utf-8"
    ) == "hello\nhello\n"


def test_edit_file_rejects_path_escape(tmp_path: Path):
    tool = EditFileTool(tmp_path)

    result = tool.execute(
        "../outside.txt",
        "old",
        "new",
    )

    assert result.success is False
    assert (
        "outside the allowed base directory"
        in result.error
    )


def test_edit_file_rejects_directory(tmp_path: Path):
    directory = tmp_path / "src"
    directory.mkdir()

    tool = EditFileTool(tmp_path)

    result = tool.execute(
        "src",
        "old",
        "new",
    )

    assert result.success is False
    assert "Path is not a file" in result.error


def test_edit_file_rejects_empty_path(tmp_path: Path):
    tool = EditFileTool(tmp_path)

    result = tool.execute(
        "",
        "old",
        "new",
    )

    assert result.success is False
    assert "No file path supplied" in result.error


def test_edit_file_rejects_empty_old_text(tmp_path: Path):
    tool = EditFileTool(tmp_path)

    result = tool.execute(
        "example.txt",
        "",
        "new",
    )

    assert result.success is False
    assert "No old text supplied" in result.error


def test_edit_file_accepts_shared_workspace(tmp_path: Path):
    target = tmp_path / "example.txt"

    target.write_text(
        "before",
        encoding="utf-8",
    )

    workspace = Workspace(tmp_path)
    tool = EditFileTool(workspace=workspace)

    result = tool.execute(
        "example.txt",
        "before",
        "after",
    )

    assert result.success is True
    assert target.read_text(
        encoding="utf-8"
    ) == "after"
