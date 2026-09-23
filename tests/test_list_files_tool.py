from pathlib import Path

from tools.list_files_tool import ListFilesTool


def test_list_files_lists_files_and_directories(tmp_path: Path):
    (tmp_path / "alpha.txt").write_text(
        "alpha",
        encoding="utf-8",
    )

    (tmp_path / "beta.txt").write_text(
        "beta",
        encoding="utf-8",
    )

    (tmp_path / "src").mkdir()

    tool = ListFilesTool(tmp_path)

    result = tool.execute()

    assert result.tool_name == "list_files"
    assert result.success is True

    assert result.result == [
        {
            "name": "src",
            "type": "directory",
        },
        {
            "name": "alpha.txt",
            "type": "file",
        },
        {
            "name": "beta.txt",
            "type": "file",
        },
    ]


def test_list_files_lists_nested_directory(tmp_path: Path):
    nested = tmp_path / "src"
    nested.mkdir()

    (nested / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )

    tool = ListFilesTool(tmp_path)

    result = tool.execute("src")

    assert result.success is True
    assert result.result == [
        {
            "name": "main.py",
            "type": "file",
        }
    ]


def test_list_files_rejects_missing_directory(tmp_path: Path):
    tool = ListFilesTool(tmp_path)

    result = tool.execute("missing")

    assert result.success is False
    assert "does not exist" in result.error


def test_list_files_rejects_file(tmp_path: Path):
    target = tmp_path / "example.txt"
    target.write_text(
        "hello",
        encoding="utf-8",
    )

    tool = ListFilesTool(tmp_path)

    result = tool.execute("example.txt")

    assert result.success is False
    assert "not a directory" in result.error


def test_list_files_rejects_path_escape(tmp_path: Path):
    outside = tmp_path.parent / "outside-directory"
    outside.mkdir(exist_ok=True)

    tool = ListFilesTool(tmp_path)

    result = tool.execute("../outside-directory")

    assert result.success is False
    assert "outside the allowed base directory" in result.error
