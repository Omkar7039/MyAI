from pathlib import Path

from tools.create_directory_tool import CreateDirectoryTool
from tools.workspace import Workspace


def test_create_directory_creates_directory(tmp_path: Path):
    tool = CreateDirectoryTool(tmp_path)

    result = tool.execute("src")

    assert result.success is True
    assert result.result["path"] == "src"
    assert result.result["created"] is True
    assert (tmp_path / "src").is_dir()


def test_create_directory_creates_nested_directories(tmp_path: Path):
    tool = CreateDirectoryTool(tmp_path)

    result = tool.execute("src/core/utils")

    assert result.success is True
    assert (tmp_path / "src/core/utils").is_dir()


def test_create_directory_rejects_existing_directory(tmp_path: Path):
    directory = tmp_path / "src"
    directory.mkdir()

    tool = CreateDirectoryTool(tmp_path)

    result = tool.execute("src")

    assert result.success is False
    assert "Directory already exists" in result.error


def test_create_directory_rejects_existing_file(tmp_path: Path):
    target = tmp_path / "example.txt"
    target.write_text(
        "hello",
        encoding="utf-8",
    )

    tool = CreateDirectoryTool(tmp_path)

    result = tool.execute("example.txt")

    assert result.success is False
    assert "not a directory" in result.error


def test_create_directory_rejects_path_escape(tmp_path: Path):
    tool = CreateDirectoryTool(tmp_path)

    result = tool.execute("../outside")

    assert result.success is False
    assert (
        "outside the allowed base directory"
        in result.error
    )


def test_create_directory_rejects_empty_path(tmp_path: Path):
    tool = CreateDirectoryTool(tmp_path)

    result = tool.execute("")

    assert result.success is False
    assert "No directory path supplied" in result.error


def test_create_directory_accepts_shared_workspace(tmp_path: Path):
    workspace = Workspace(tmp_path)
    tool = CreateDirectoryTool(workspace=workspace)

    result = tool.execute("shared")

    assert result.success is True
    assert (tmp_path / "shared").is_dir()
