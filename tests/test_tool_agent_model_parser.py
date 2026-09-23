import json

import pytest

from core.tool_agent_model_parser import (
    ModelToolInstruction,
    ToolAgentModelParser,
)


def payload(**values):
    return json.dumps(values)


def test_parse_complete_instruction():
    response = payload(
        action="complete",
        reason="The requested inspection is complete.",
        tool_name=None,
    )

    result = ToolAgentModelParser().parse(response)

    assert isinstance(result, ModelToolInstruction)
    assert result.action == "complete"
    assert result.reason == "The requested inspection is complete."
    assert result.tool_name is None
    assert result.raw_response == response


def test_parse_continue_instruction():
    response = payload(
        action="continue",
        reason="The file must be inspected next.",
        tool_name="read_file",
    )

    result = ToolAgentModelParser().parse(response)

    assert result.action == "continue"
    assert result.reason == "The file must be inspected next."
    assert result.tool_name == "read_file"


def test_parse_stop_instruction():
    response = payload(
        action="stop",
        reason="The previous operation failed.",
        tool_name=None,
    )

    result = ToolAgentModelParser().parse(response)

    assert result.action == "stop"
    assert result.tool_name is None


def test_parse_json_fenced_response():
    response = "```json\n" + payload(
        action="continue",
        reason="Another observation is required.",
        tool_name="read_file",
    ) + "\n```"

    result = ToolAgentModelParser().parse(response)

    assert result.action == "continue"
    assert result.tool_name == "read_file"


def test_parse_strips_reason_and_tool_name():
    response = payload(
        action="continue",
        reason="  inspect the file  ",
        tool_name="  read_file  ",
    )

    result = ToolAgentModelParser().parse(response)

    assert result.reason == "inspect the file"
    assert result.tool_name == "read_file"


def test_empty_response_is_rejected():
    with pytest.raises(ValueError, match="Model response is empty"):
        ToolAgentModelParser().parse("")


def test_non_json_response_is_rejected():
    with pytest.raises(ValueError, match="valid JSON"):
        ToolAgentModelParser().parse(
            "I think the task is complete."
        )


def test_json_array_is_rejected():
    with pytest.raises(ValueError, match="JSON object"):
        ToolAgentModelParser().parse(
            '[{"action": "complete"}]'
        )


def test_unknown_action_is_rejected():
    with pytest.raises(ValueError, match="action must be one of"):
        ToolAgentModelParser().parse(
            payload(
                action="execute",
                reason="Run a tool.",
                tool_name="read_file",
            )
        )


def test_missing_reason_is_rejected():
    with pytest.raises(
        ValueError,
        match="reason must be a non-empty string",
    ):
        ToolAgentModelParser().parse(
            payload(action="complete")
        )


def test_empty_reason_is_rejected():
    with pytest.raises(
        ValueError,
        match="reason must be a non-empty string",
    ):
        ToolAgentModelParser().parse(
            payload(
                action="complete",
                reason="   ",
            )
        )


def test_non_string_tool_name_is_rejected():
    with pytest.raises(
        ValueError,
        match="tool_name must be a string",
    ):
        ToolAgentModelParser().parse(
            payload(
                action="continue",
                reason="Need another step.",
                tool_name=123,
            )
        )


def test_tool_name_not_allowed_for_complete():
    with pytest.raises(
        ValueError,
        match="tool_name is only allowed",
    ):
        ToolAgentModelParser().parse(
            payload(
                action="complete",
                reason="Done.",
                tool_name="read_file",
            )
        )


def test_tool_name_not_allowed_for_stop():
    with pytest.raises(
        ValueError,
        match="tool_name is only allowed",
    ):
        ToolAgentModelParser().parse(
            payload(
                action="stop",
                reason="Stopped.",
                tool_name="read_file",
            )
        )


def test_unsupported_fields_are_rejected():
    with pytest.raises(ValueError, match="unsupported fields"):
        ToolAgentModelParser().parse(
            payload(
                action="complete",
                reason="Done.",
                confidence=1.0,
            )
        )


def test_non_string_response_is_rejected():
    with pytest.raises(
        TypeError,
        match="response must be a string",
    ):
        ToolAgentModelParser().parse(123)


def test_parser_does_not_execute_tools():
    response = payload(
        action="continue",
        reason="Need another step.",
        tool_name="delete_file",
    )

    result = ToolAgentModelParser().parse(response)

    assert result.tool_name == "delete_file"
