import hashlib

from tools.file_hash_tool import FileHashTool
from tools.workspace import Workspace


def test_calculates_sha256(tmp_path):
    tool = FileHashTool(base_directory=tmp_path)

    content = b"hello world"
    (tmp_path / "example.txt").write_bytes(content)

    result = tool.execute("example.txt")

    expected = hashlib.sha256(content).hexdigest()

    assert result.success is True
    assert result.result["path"] == "example.txt"
    assert result.result["algorithm"] == "sha256"
    assert result.result["hash"] == expected


def test_hash_is_deterministic(tmp_path):
    tool = FileHashTool(base_directory=tmp_path)

    (tmp_path / "example.txt").write_text(
        "same content",
        encoding="utf-8",
    )

    first = tool.execute("example.txt")
    second = tool.execute("example.txt")

    assert first.success is True
    assert second.success is True
    assert first.result["hash"] == second.result["hash"]


def test_hash_changes_when_file_changes(tmp_path):
    tool = FileHashTool(base_directory=tmp_path)

    target = tmp_path / "example.txt"
    target.write_text("before", encoding="utf-8")

    first = tool.execute("example.txt")

    target.write_text("after", encoding="utf-8")

    second = tool.execute("example.txt")

    assert first.success is True
    assert second.success is True
    assert first.result["hash"] != second.result["hash"]


def test_handles_binary_file(tmp_path):
    tool = FileHashTool(base_directory=tmp_path)

    content = bytes(range(256))
    (tmp_path / "binary.bin").write_bytes(content)

    result = tool.execute("binary.bin")

    assert result.success is True
    assert result.result["hash"] == hashlib.sha256(content).hexdigest()


def test_rejects_missing_file(tmp_path):
    tool = FileHashTool(base_directory=tmp_path)

    result = tool.execute("missing.txt")

    assert result.success is False
    assert "does not exist" in result.error


def test_rejects_directory(tmp_path):
    tool = FileHashTool(base_directory=tmp_path)

    (tmp_path / "directory").mkdir()

    result = tool.execute("directory")

    assert result.success is False
    assert "not a file" in result.error


def test_rejects_path_escape(tmp_path):
    tool = FileHashTool(base_directory=tmp_path)

    result = tool.execute("../outside.txt")

    assert result.success is False
    assert "outside the allowed base directory" in result.error


def test_rejects_empty_path(tmp_path):
    tool = FileHashTool(base_directory=tmp_path)

    result = tool.execute("")

    assert result.success is False
    assert "No file path supplied" in result.error


def test_accepts_shared_workspace(tmp_path):
    workspace = Workspace(tmp_path)
    tool = FileHashTool(workspace=workspace)

    assert tool.workspace is workspace
