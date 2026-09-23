from tools.file_exists_tool import FileExistsTool
from tools.workspace import Workspace


def test_detects_existing_file(tmp_path):
    tool = FileExistsTool(base_directory=tmp_path)

    (tmp_path / "example.txt").write_text(
        "hello",
        encoding="utf-8",
    )

    result = tool.execute("example.txt")

    assert result.success is True
    assert result.result["exists"] is True
    assert result.result["type"] == "file"
    assert result.result["path"] == "example.txt"


def test_detects_existing_directory(tmp_path):
    tool = FileExistsTool(base_directory=tmp_path)

    (tmp_path / "src").mkdir()

    result = tool.execute("src")

    assert result.success is True
    assert result.result["exists"] is True
    assert result.result["type"] == "directory"


def test_reports_missing_path(tmp_path):
    tool = FileExistsTool(base_directory=tmp_path)

    result = tool.execute("missing.txt")

    assert result.success is True
    assert result.result["exists"] is False
    assert result.result["type"] is None


def test_handles_nested_path(tmp_path):
    tool = FileExistsTool(base_directory=tmp_path)

    (tmp_path / "src" / "core").mkdir(parents=True)
    (tmp_path / "src" / "core" / "main.py").write_text(
        "main",
        encoding="utf-8",
    )

    result = tool.execute("src/core/main.py")

    assert result.success is True
    assert result.result["exists"] is True
    assert result.result["type"] == "file"


def test_rejects_path_escape(tmp_path):
    tool = FileExistsTool(base_directory=tmp_path)

    result = tool.execute("../outside.txt")

    assert result.success is False
    assert "outside the allowed base directory" in result.error


def test_rejects_empty_path(tmp_path):
    tool = FileExistsTool(base_directory=tmp_path)

    result = tool.execute("")

    assert result.success is False
    assert "No path supplied" in result.error


def test_accepts_shared_workspace(tmp_path):
    workspace = Workspace(tmp_path)
    tool = FileExistsTool(workspace=workspace)

    assert tool.workspace is workspace
