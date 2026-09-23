from tools.get_file_info_tool import GetFileInfoTool
from tools.workspace import Workspace


def test_returns_file_info(tmp_path):
    tool = GetFileInfoTool(base_directory=tmp_path)

    target = tmp_path / "example.txt"
    target.write_text("hello", encoding="utf-8")

    result = tool.execute("example.txt")

    assert result.success is True
    assert result.result["path"] == "example.txt"
    assert result.result["type"] == "file"
    assert result.result["size"] == 5
    assert result.result["child_count"] is None
    assert isinstance(result.result["modified_time"], float)


def test_returns_directory_info(tmp_path):
    tool = GetFileInfoTool(base_directory=tmp_path)

    target = tmp_path / "src"
    target.mkdir()
    (target / "a.py").write_text("a", encoding="utf-8")
    (target / "b.py").write_text("b", encoding="utf-8")

    result = tool.execute("src")

    assert result.success is True
    assert result.result["path"] == "src"
    assert result.result["type"] == "directory"
    assert result.result["child_count"] == 2


def test_returns_zero_children_for_empty_directory(tmp_path):
    tool = GetFileInfoTool(base_directory=tmp_path)

    (tmp_path / "empty").mkdir()

    result = tool.execute("empty")

    assert result.success is True
    assert result.result["type"] == "directory"
    assert result.result["child_count"] == 0


def test_rejects_missing_path(tmp_path):
    tool = GetFileInfoTool(base_directory=tmp_path)

    result = tool.execute("missing.txt")

    assert result.success is False
    assert "does not exist" in result.error


def test_rejects_path_escape(tmp_path):
    tool = GetFileInfoTool(base_directory=tmp_path)

    result = tool.execute("../outside.txt")

    assert result.success is False
    assert "outside the allowed base directory" in result.error


def test_rejects_empty_path(tmp_path):
    tool = GetFileInfoTool(base_directory=tmp_path)

    result = tool.execute("")

    assert result.success is False
    assert "No path supplied" in result.error


def test_accepts_shared_workspace(tmp_path):
    workspace = Workspace(tmp_path)
    tool = GetFileInfoTool(workspace=workspace)

    assert tool.workspace is workspace
