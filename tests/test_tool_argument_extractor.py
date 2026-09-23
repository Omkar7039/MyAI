import pytest

from core.tool_argument_extractor import (
    ToolArgumentExtractor,
    ToolArguments,
)


def test_extract_read_file_path():
    result = ToolArgumentExtractor().extract(
        "read_file",
        "Read the file config.py",
    )

    assert isinstance(result, ToolArguments)
    assert result.tool_name == "read_file"
    assert result.arguments == {
        "path": "config.py",
    }


def test_extract_read_file_line_range():
    result = ToolArgumentExtractor().extract(
        "read_file",
        "Read config.py lines 10 to 20",
    )

    assert result.arguments == {
        "path": "config.py",
        "start_line": 10,
        "end_line": 20,
    }


def test_extract_list_files_without_path():
    result = ToolArgumentExtractor().extract(
        "list_files",
        "List the files here",
    )

    assert result.arguments == {}


def test_extract_list_files_with_path():
    result = ToolArgumentExtractor().extract(
        "list_files",
        "List files in src",
    )

    assert result.arguments == {
        "path": "src",
    }


def test_extract_directory_tree():
    result = ToolArgumentExtractor().extract(
        "directory_tree",
        "Show the project tree depth 2",
    )

    assert result.arguments == {
        "max_depth": 2,
    }


def test_extract_search_files():
    result = ToolArgumentExtractor().extract(
        "search_files",
        "Search for TODO in src",
    )

    assert result.arguments == {
        "query": "TODO",
        "path": "src",
    }


def test_extract_file_exists():
    result = ToolArgumentExtractor().extract(
        "file_exists",
        "Check if config.py exists",
    )

    assert result.arguments == {
        "path": "config.py",
    }


def test_extract_file_info():
    result = ToolArgumentExtractor().extract(
        "get_file_info",
        "Show information about config.py",
    )

    assert result.arguments == {
        "path": "config.py",
    }


def test_extract_file_hash():
    result = ToolArgumentExtractor().extract(
        "file_hash",
        "Calculate SHA-256 for config.py",
    )

    assert result.arguments == {
        "path": "config.py",
    }


def test_extract_delete_file():
    result = ToolArgumentExtractor().extract(
        "delete_file",
        "Delete the file old.py",
    )

    assert result.arguments == {
        "path": "old.py",
    }


def test_extract_create_directory():
    result = ToolArgumentExtractor().extract(
        "create_directory",
        "Create directory src/new_module",
    )

    assert result.arguments == {
        "path": "src/new_module",
    }


def test_extract_write_file():
    result = ToolArgumentExtractor().extract(
        "write_file",
        "Create file example.py with content: print('hello')",
    )

    assert result.arguments["path"] == "example.py"
    assert result.arguments["content"] == "print('hello')"


def test_unknown_tool_returns_empty_arguments():
    result = ToolArgumentExtractor().extract(
        "unknown_tool",
        "Do something",
    )

    assert result.arguments == {}


def test_empty_tool_name_rejected():
    with pytest.raises(ValueError):
        ToolArgumentExtractor().extract(
            "",
            "Read config.py",
        )


def test_empty_request_rejected():
    with pytest.raises(ValueError):
        ToolArgumentExtractor().extract(
            "read_file",
            "",
        )
