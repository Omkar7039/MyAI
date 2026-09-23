from pathlib import Path

from tools.search_files_tool import SearchFilesTool


def test_search_files_finds_matching_lines(tmp_path: Path):
    target = tmp_path / "main.py"

    target.write_text(
        "def hello():\n"
        "    print('hello')\n"
        "def goodbye():\n",
        encoding="utf-8",
    )

    tool = SearchFilesTool(tmp_path)

    result = tool.execute("hello")

    assert result.tool_name == "search_files"
    assert result.success is True
    assert result.result == [
        {
            "path": "main.py",
            "line": 1,
            "text": "def hello():",
        },
        {
            "path": "main.py",
            "line": 2,
            "text": "    print('hello')",
        },
    ]


def test_search_files_searches_nested_files(tmp_path: Path):
    source = tmp_path / "src"
    source.mkdir()

    target = source / "app.py"

    target.write_text(
        "def target_function():\n"
        "    return 42\n",
        encoding="utf-8",
    )

    tool = SearchFilesTool(tmp_path)

    result = tool.execute("target_function")

    assert result.success is True
    assert result.result == [
        {
            "path": "src/app.py",
            "line": 1,
            "text": "def target_function():",
        }
    ]


def test_search_files_returns_empty_for_no_match(tmp_path: Path):
    target = tmp_path / "example.py"

    target.write_text(
        "print('hello')\n",
        encoding="utf-8",
    )

    tool = SearchFilesTool(tmp_path)

    result = tool.execute("missing")

    assert result.success is True
    assert result.result == []


def test_search_files_rejects_empty_query(tmp_path: Path):
    tool = SearchFilesTool(tmp_path)

    result = tool.execute("")

    assert result.success is False
    assert "No search query supplied" in result.error


def test_search_files_rejects_path_escape(tmp_path: Path):
    outside = tmp_path.parent / "outside-search"

    outside.mkdir(exist_ok=True)

    target = outside / "secret.txt"

    target.write_text(
        "secret",
        encoding="utf-8",
    )

    tool = SearchFilesTool(tmp_path)

    result = tool.execute(
        "secret",
        "../outside-search",
    )

    assert result.success is False
    assert "outside the allowed base directory" in result.error
