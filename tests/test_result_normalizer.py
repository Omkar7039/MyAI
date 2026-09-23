from dataclasses import dataclass

from tools.base import ToolResult
from tools.result_normalizer import ToolResultNormalizer


@dataclass
class SampleResult:
    name: str
    count: int


def test_normalize_tool_result():
    result = ToolResult(
        tool_name="read_file",
        success=True,
        result="hello",
    )

    normalized = ToolResultNormalizer.normalize(result)

    assert normalized == {
        "tool_name": "read_file",
        "success": True,
        "result": "hello",
        "error": None,
    }


def test_normalize_failed_tool_result():
    result = ToolResult(
        tool_name="read_file",
        success=False,
        error="File does not exist.",
    )

    normalized = ToolResultNormalizer.normalize(result)

    assert normalized == {
        "tool_name": "read_file",
        "success": False,
        "result": None,
        "error": "File does not exist.",
    }


def test_normalize_dataclass_result():
    result = SampleResult(
        name="example",
        count=3,
    )

    normalized = ToolResultNormalizer.normalize(result)

    assert normalized["success"] is True
    assert normalized["result"] == {
        "name": "example",
        "count": 3,
    }


def test_normalize_nested_values():
    result = {
        "items": [
            SampleResult("one", 1),
            SampleResult("two", 2),
        ],
        "metadata": {
            "enabled": True,
        },
    }

    normalized = ToolResultNormalizer.normalize(result)

    assert normalized["result"] == {
        "items": [
            {"name": "one", "count": 1},
            {"name": "two", "count": 2},
        ],
        "metadata": {
            "enabled": True,
        },
    }


def test_normalize_tuple():
    normalized = ToolResultNormalizer.normalize(
        ("one", "two")
    )

    assert normalized["result"] == ["one", "two"]


def test_normalize_unknown_object():
    class CustomObject:
        def __str__(self):
            return "custom-value"

    normalized = ToolResultNormalizer.normalize(
        CustomObject()
    )

    assert normalized["result"] == "custom-value"
