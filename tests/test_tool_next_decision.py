from core.tool_next_decision import NextDecision, ToolNextDecisionEngine
from core.tool_result_observer import ToolObservation


def successful(tool_name="read_file", result="VALUE = 42\n"):
    return ToolObservation(
        tool_name=tool_name,
        success=True,
        result=result,
        error=None,
        executed=True,
    )


def failed(tool_name="read_file"):
    return ToolObservation(
        tool_name=tool_name,
        success=False,
        result=None,
        error="tool failed",
        executed=True,
    )


def not_executed(tool_name="delete_file"):
    return ToolObservation(
        tool_name=tool_name,
        success=False,
        result=None,
        error=None,
        executed=False,
    )


def test_successful_single_step_completes():
    result = ToolNextDecisionEngine().decide(
        "Read the file config.py",
        successful(),
    )

    assert isinstance(result, NextDecision)
    assert result.action == "complete"
    assert result.tool_name == "read_file"


def test_explicit_follow_up_requests_continuation():
    result = ToolNextDecisionEngine().decide(
        "Read config.py and then verify the value",
        successful(),
    )

    assert result.action == "continue"
    assert result.tool_name == "read_file"


def test_then_marker_requests_continuation():
    result = ToolNextDecisionEngine().decide(
        "List the files in src, then check the result",
        successful("list_files", {"entries": ["main.py"]}),
    )

    assert result.action == "continue"
    assert result.tool_name == "list_files"


def test_failed_tool_stops():
    result = ToolNextDecisionEngine().decide(
        "Read missing.py",
        failed(),
    )

    assert result.action == "stop"
    assert result.tool_name == "read_file"


def test_not_executed_stops():
    result = ToolNextDecisionEngine().decide(
        "Delete important.txt",
        not_executed(),
    )

    assert result.action == "stop"
    assert result.tool_name == "delete_file"


def test_unknown_request_without_execution_stops():
    observation = ToolObservation(
        tool_name=None,
        success=False,
        result=None,
        error=None,
        executed=False,
    )

    result = ToolNextDecisionEngine().decide(
        "Tell me something interesting",
        observation,
    )

    assert result.action == "stop"
    assert result.tool_name is None


def test_successful_write_without_follow_up_completes():
    result = ToolNextDecisionEngine().decide(
        "Create example.py with the requested content",
        successful("write_file", {"path": "example.py"}),
    )

    assert result.action == "complete"
    assert result.tool_name == "write_file"
