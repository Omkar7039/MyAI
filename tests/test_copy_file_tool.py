from tools.copy_file_tool import CopyFileTool
from tools.workspace import Workspace


def test_copies_file(tmp_path):
    tool = CopyFileTool(base_directory=tmp_path)

    source = tmp_path / "source.txt"
    source.write_text("hello", encoding="utf-8")

    result = tool.execute("source.txt", "copy.txt")

    assert result.success is True
    assert source.exists()
    assert (tmp_path / "copy.txt").read_text(
        encoding="utf-8"
    ) == "hello"


def test_copies_directory(tmp_path):
    tool = CopyFileTool(base_directory=tmp_path)

    source = tmp_path / "source"
    source.mkdir()
    (source / "file.txt").write_text(
        "hello",
        encoding="utf-8",
    )

    result = tool.execute("source", "copy")

    assert result.success is True
    assert source.exists()
    assert (tmp_path / "copy" / "file.txt").read_text(
        encoding="utf-8"
    ) == "hello"


def test_creates_destination_parent_directories(tmp_path):
    tool = CopyFileTool(base_directory=tmp_path)

    source = tmp_path / "file.txt"
    source.write_text("hello", encoding="utf-8")

    result = tool.execute(
        "file.txt",
        "nested/deep/copy.txt",
    )

    assert result.success is True
    assert (tmp_path / "nested/deep/copy.txt").read_text(
        encoding="utf-8"
    ) == "hello"


def test_rejects_missing_source(tmp_path):
    tool = CopyFileTool(base_directory=tmp_path)

    result = tool.execute("missing.txt", "copy.txt")

    assert result.success is False
    assert "does not exist" in result.error


def test_rejects_existing_destination(tmp_path):
    tool = CopyFileTool(base_directory=tmp_path)

    (tmp_path / "source.txt").write_text(
        "source",
        encoding="utf-8",
    )
    (tmp_path / "copy.txt").write_text(
        "existing",
        encoding="utf-8",
    )

    result = tool.execute("source.txt", "copy.txt")

    assert result.success is False
    assert "already exists" in result.error


def test_rejects_source_path_escape(tmp_path):
    tool = CopyFileTool(base_directory=tmp_path)

    result = tool.execute("../outside.txt", "inside.txt")

    assert result.success is False
    assert "outside the allowed base directory" in result.error


def test_rejects_destination_path_escape(tmp_path):
    tool = CopyFileTool(base_directory=tmp_path)

    (tmp_path / "source.txt").write_text(
        "hello",
        encoding="utf-8",
    )

    result = tool.execute(
        "source.txt",
        "../outside.txt",
    )

    assert result.success is False
    assert "outside the allowed base directory" in result.error


def test_rejects_empty_source(tmp_path):
    tool = CopyFileTool(base_directory=tmp_path)

    result = tool.execute("", "copy.txt")

    assert result.success is False
    assert "No source path supplied" in result.error


def test_rejects_empty_destination(tmp_path):
    tool = CopyFileTool(base_directory=tmp_path)

    result = tool.execute("source.txt", "")

    assert result.success is False
    assert "No destination path supplied" in result.error


def test_accepts_shared_workspace(tmp_path):
    workspace = Workspace(tmp_path)
    tool = CopyFileTool(workspace=workspace)

    assert tool.workspace is workspace
