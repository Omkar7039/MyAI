from pathlib import Path

from tools.file_tool import ReadFileTool


def test_read_file_reads_text(tmp_path: Path):
    target = tmp_path / "example.txt"
    target.write_text(
        "hello MyAI",
        encoding="utf-8",
    )

    tool = ReadFileTool(tmp_path)

    result = tool.execute("example.txt")

    assert result.tool_name == "read_file"
    assert result.success is True
    assert result.result == "hello MyAI"


def test_read_file_rejects_empty_path(tmp_path: Path):
    tool = ReadFileTool(tmp_path)

    result = tool.execute("")

    assert result.success is False
    assert "No file path supplied" in result.error


def test_read_file_rejects_missing_file(tmp_path: Path):
    tool = ReadFileTool(tmp_path)

    result = tool.execute("missing.txt")

    assert result.success is False
    assert "does not exist" in result.error


def test_read_file_rejects_directory(tmp_path: Path):
    directory = tmp_path / "directory"
    directory.mkdir()

    tool = ReadFileTool(tmp_path)

    result = tool.execute("directory")

    assert result.success is False
    assert "not a file" in result.error


def test_read_file_rejects_path_escape(tmp_path: Path):
    outside = tmp_path.parent / "outside.txt"
    outside.write_text(
        "secret",
        encoding="utf-8",
    )

    tool = ReadFileTool(tmp_path)

    result = tool.execute("../outside.txt")

    assert result.success is False
    assert "outside the allowed base directory" in result.error


def test_read_file_supports_start_line(tmp_path):
    tool = ReadFileTool(base_directory=tmp_path)

    (tmp_path / "example.txt").write_text(
        "one\ntwo\nthree\nfour\n",
        encoding="utf-8",
    )

    result = tool.execute(
        "example.txt",
        start_line=2,
    )

    assert result.success is True
    assert result.result == "two\nthree\nfour\n"


def test_read_file_supports_end_line(tmp_path):
    tool = ReadFileTool(base_directory=tmp_path)

    (tmp_path / "example.txt").write_text(
        "one\ntwo\nthree\nfour\n",
        encoding="utf-8",
    )

    result = tool.execute(
        "example.txt",
        end_line=2,
    )

    assert result.success is True
    assert result.result == "one\ntwo\n"


def test_read_file_supports_line_range(tmp_path):
    tool = ReadFileTool(base_directory=tmp_path)

    (tmp_path / "example.txt").write_text(
        "one\ntwo\nthree\nfour\n",
        encoding="utf-8",
    )

    result = tool.execute(
        "example.txt",
        start_line=2,
        end_line=3,
    )

    assert result.success is True
    assert result.result == "two\nthree\n"


def test_read_file_rejects_invalid_start_line(tmp_path):
    tool = ReadFileTool(base_directory=tmp_path)

    result = tool.execute(
        "example.txt",
        start_line=0,
    )

    assert result.success is False
    assert "start_line must be at least 1" in result.error


def test_read_file_rejects_invalid_end_line(tmp_path):
    tool = ReadFileTool(base_directory=tmp_path)

    result = tool.execute(
        "example.txt",
        end_line=0,
    )

    assert result.success is False
    assert "end_line must be at least 1" in result.error


def test_read_file_rejects_reversed_line_range(tmp_path):
    tool = ReadFileTool(base_directory=tmp_path)

    result = tool.execute(
        "example.txt",
        start_line=4,
        end_line=2,
    )

    assert result.success is False
    assert "start_line cannot be greater than end_line" in result.error


def test_read_file_rejects_non_integer_line_number(tmp_path):
    tool = ReadFileTool(base_directory=tmp_path)

    result = tool.execute(
        "example.txt",
        start_line="2",
    )

    assert result.success is False
    assert "start_line must be an integer" in result.error
