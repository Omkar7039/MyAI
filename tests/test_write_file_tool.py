from pathlib import Path

from tools.write_file_tool import WriteFileTool
from tools.workspace import Workspace


def test_write_file_creates_file(tmp_path: Path):
    tool = WriteFileTool(tmp_path)

    result = tool.execute(
        "example.txt",
        "hello",
    )

    assert result.success is True
    assert result.result["path"] == "example.txt"
    assert result.result["bytes"] == 5

    assert (
        (tmp_path / "example.txt").read_text(
            encoding="utf-8"
        )
        == "hello"
    )


def test_write_file_overwrites_existing_file(tmp_path: Path):
    target = tmp_path / "example.txt"
    target.write_text(
        "old",
        encoding="utf-8",
    )

    tool = WriteFileTool(tmp_path)

    result = tool.execute(
        "example.txt",
        "new content",
    )

    assert result.success is True
    assert target.read_text(
        encoding="utf-8"
    ) == "new content"


def test_write_file_creates_parent_directories(tmp_path: Path):
    tool = WriteFileTool(tmp_path)

    result = tool.execute(
        "src/core/example.py",
        "print('hello')",
    )

    assert result.success is True

    target = tmp_path / "src/core/example.py"

    assert target.exists()
    assert target.read_text(
        encoding="utf-8"
    ) == "print('hello')"


def test_write_file_rejects_path_escape(tmp_path: Path):
    tool = WriteFileTool(tmp_path)

    result = tool.execute(
        "../outside.txt",
        "secret",
    )

    assert result.success is False
    assert (
        "outside the allowed base directory"
        in result.error
    )


def test_write_file_rejects_directory(tmp_path: Path):
    directory = tmp_path / "src"
    directory.mkdir()

    tool = WriteFileTool(tmp_path)

    result = tool.execute(
        "src",
        "content",
    )

    assert result.success is False
    assert "Path is not a file" in result.error


def test_write_file_rejects_empty_path(tmp_path: Path):
    tool = WriteFileTool(tmp_path)

    result = tool.execute(
        "",
        "content",
    )

    assert result.success is False
    assert "No file path supplied" in result.error


def test_write_file_accepts_shared_workspace(tmp_path: Path):
    workspace = Workspace(tmp_path)
    tool = WriteFileTool(workspace=workspace)

    result = tool.execute(
        "shared.txt",
        "workspace",
    )

    assert result.success is True
    assert (
        (tmp_path / "shared.txt").read_text(
            encoding="utf-8"
        )
        == "workspace"
    )
