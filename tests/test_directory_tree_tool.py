from tools.directory_tree_tool import DirectoryTreeTool
from tools.workspace import Workspace


def test_returns_directory_tree(tmp_path):
    tool = DirectoryTreeTool(base_directory=tmp_path)

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "readme",
        encoding="utf-8",
    )

    result = tool.execute()

    assert result.success is True

    entries = result.result["entries"]

    assert entries == [
        {
            "path": "src",
            "name": "src",
            "type": "directory",
            "depth": 1,
        },
        {
            "path": "src/main.py",
            "name": "main.py",
            "type": "file",
            "depth": 2,
        },
        {
            "path": "README.md",
            "name": "README.md",
            "type": "file",
            "depth": 1,
        },
    ]


def test_respects_max_depth(tmp_path):
    tool = DirectoryTreeTool(base_directory=tmp_path)

    (tmp_path / "a" / "b" / "c").mkdir(parents=True)
    (tmp_path / "a" / "b" / "c" / "deep.txt").write_text(
        "deep",
        encoding="utf-8",
    )

    result = tool.execute(".", max_depth=1)

    assert result.success is True

    paths = [
        entry["path"]
        for entry in result.result["entries"]
    ]

    assert "a" in paths
    assert "a/b" in paths
    assert "a/b/c" not in paths
    assert "a/b/c/deep.txt" not in paths


def test_zero_depth_returns_immediate_children_only(tmp_path):
    tool = DirectoryTreeTool(base_directory=tmp_path)

    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "file.txt").write_text(
        "hello",
        encoding="utf-8",
    )
    (tmp_path / "root.txt").write_text(
        "root",
        encoding="utf-8",
    )

    result = tool.execute(".", max_depth=0)

    assert result.success is True

    paths = [
        entry["path"]
        for entry in result.result["entries"]
    ]

    assert "nested" in paths
    assert "root.txt" in paths
    assert "nested/file.txt" not in paths


def test_returns_requested_subdirectory(tmp_path):
    tool = DirectoryTreeTool(base_directory=tmp_path)

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text(
        "main",
        encoding="utf-8",
    )

    result = tool.execute("src")

    assert result.success is True
    assert result.result["path"] == "src"
    assert result.result["entries"][0]["path"] == "src/main.py"


def test_rejects_missing_directory(tmp_path):
    tool = DirectoryTreeTool(base_directory=tmp_path)

    result = tool.execute("missing")

    assert result.success is False
    assert "does not exist" in result.error


def test_rejects_file_path(tmp_path):
    tool = DirectoryTreeTool(base_directory=tmp_path)

    (tmp_path / "file.txt").write_text(
        "hello",
        encoding="utf-8",
    )

    result = tool.execute("file.txt")

    assert result.success is False
    assert "not a directory" in result.error


def test_rejects_path_escape(tmp_path):
    tool = DirectoryTreeTool(base_directory=tmp_path)

    result = tool.execute("../outside")

    assert result.success is False
    assert "outside the allowed base directory" in result.error


def test_rejects_empty_path(tmp_path):
    tool = DirectoryTreeTool(base_directory=tmp_path)

    result = tool.execute("")

    assert result.success is False
    assert "No directory path supplied" in result.error


def test_rejects_negative_depth(tmp_path):
    tool = DirectoryTreeTool(base_directory=tmp_path)

    result = tool.execute(".", max_depth=-1)

    assert result.success is False
    assert "zero or greater" in result.error


def test_rejects_non_integer_depth(tmp_path):
    tool = DirectoryTreeTool(base_directory=tmp_path)

    result = tool.execute(".", max_depth="2")

    assert result.success is False
    assert "must be an integer" in result.error


def test_accepts_shared_workspace(tmp_path):
    workspace = Workspace(tmp_path)
    tool = DirectoryTreeTool(workspace=workspace)

    assert tool.workspace is workspace
