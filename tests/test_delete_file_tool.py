from pathlib import Path

from tools.delete_file_tool import DeleteFileTool
from tools.workspace import Workspace


def test_delete_file_deletes_existing_file(tmp_path: Path):
    target = tmp_path / "example.txt"
    target.write_text(
        "hello",
        encoding="utf-8",
    )

    tool = DeleteFileTool(tmp_path)

    result = tool.execute("example.txt")

    assert result.success is True
    assert result.result["path"] == "example.txt"
    assert result.result["deleted"] is True
    assert not target.exists()


def test_delete_file_rejects_missing_file(tmp_path: Path):
    tool = DeleteFileTool(tmp_path)

    result = tool.execute("missing.txt")

    assert result.success is False
    assert "File does not exist" in result.error


def test_delete_file_rejects_directory(tmp_path: Path):
    directory = tmp_path / "src"
    directory.mkdir()

    tool = DeleteFileTool(tmp_path)

    result = tool.execute("src")

    assert result.success is False
    assert "Path is not a file" in result.error
    assert directory.exists()


def test_delete_file_rejects_path_escape(tmp_path: Path):
    tool = DeleteFileTool(tmp_path)

    result = tool.execute("../outside.txt")

    assert result.success is False
    assert (
        "outside the allowed base directory"
        in result.error
    )


def test_delete_file_rejects_empty_path(tmp_path: Path):
    tool = DeleteFileTool(tmp_path)

    result = tool.execute("")

    assert result.success is False
    assert "No file path supplied" in result.error


def test_delete_file_accepts_shared_workspace(tmp_path: Path):
    target = tmp_path / "shared.txt"
    target.write_text(
        "workspace",
        encoding="utf-8",
    )

    workspace = Workspace(tmp_path)
    tool = DeleteFileTool(workspace=workspace)

    result = tool.execute("shared.txt")

    assert result.success is True
    assert not target.exists()
