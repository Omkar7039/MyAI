import json

import pytest

from core.tool_agent_instruction_validator import (
    ToolAgentInstructionValidator,
    ValidatedToolInstruction,
)
from core.tool_agent_model_parser import (
    ModelToolInstruction,
    ToolAgentModelParser,
)


TOOLS = {
    "read_file",
    "list_files",
    "write_file",
    "delete_file",
    "execute_code",
}


def instruction(
    action="continue",
    reason="Need another step.",
    tool_name="read_file",
):
    return ToolAgentModelParser().parse(
        json.dumps(
            {
                "action": action,
                "reason": reason,
                "tool_name": tool_name,
            }
        )
    )


def test_registered_tool_is_accepted():
    validator = ToolAgentInstructionValidator(TOOLS)

    result = validator.validate(
        instruction(
            action="continue",
            tool_name="read_file",
        )
    )

    assert isinstance(result, ValidatedToolInstruction)
    assert result.instruction.tool_name == "read_file"


def test_unregistered_tool_is_rejected():
    validator = ToolAgentInstructionValidator(TOOLS)

    with pytest.raises(
        ValueError,
        match="Unknown tool: unknown_tool",
    ):
        validator.validate(
            instruction(
                action="continue",
                tool_name="unknown_tool",
            )
        )


def test_continue_requires_tool_name():
    validator = ToolAgentInstructionValidator(TOOLS)

    raw = ModelToolInstruction(
        action="continue",
        reason="Another step is required.",
        tool_name=None,
        raw_response="test",
    )

    with pytest.raises(
        ValueError,
        match="continue action requires tool_name",
    ):
        validator.validate(raw)


def test_complete_does_not_require_tool_name():
    validator = ToolAgentInstructionValidator(TOOLS)

    result = validator.validate(
        instruction(
            action="complete",
            reason="Task is complete.",
            tool_name=None,
        )
    )

    assert result.instruction.action == "complete"
    assert result.instruction.tool_name is None


def test_stop_does_not_require_tool_name():
    validator = ToolAgentInstructionValidator(TOOLS)

    result = validator.validate(
        instruction(
            action="stop",
            reason="Stopping.",
            tool_name=None,
        )
    )

    assert result.instruction.action == "stop"
    assert result.instruction.tool_name is None


def test_complete_with_tool_name_is_rejected():
    validator = ToolAgentInstructionValidator(TOOLS)

    raw = ModelToolInstruction(
        action="complete",
        reason="Done.",
        tool_name="read_file",
        raw_response="test",
    )

    with pytest.raises(
        ValueError,
        match="tool_name is only allowed",
    ):
        validator.validate(raw)


def test_stop_with_tool_name_is_rejected():
    validator = ToolAgentInstructionValidator(TOOLS)

    raw = ModelToolInstruction(
        action="stop",
        reason="Stopped.",
        tool_name="read_file",
        raw_response="test",
    )

    with pytest.raises(
        ValueError,
        match="tool_name is only allowed",
    ):
        validator.validate(raw)


def test_tool_name_is_normalized():
    validator = ToolAgentInstructionValidator(TOOLS)

    result = validator.validate(
        instruction(
            action="continue",
            tool_name="  READ_FILE  ",
        )
    )

    assert result.instruction.tool_name == "read_file"


def test_allowed_tools_are_exposed_as_frozen_set():
    validator = ToolAgentInstructionValidator(TOOLS)

    assert isinstance(
        validator.allowed_tools,
        frozenset,
    )
    assert validator.allowed_tools == frozenset(TOOLS)


def test_allowed_tools_are_normalized():
    validator = ToolAgentInstructionValidator(
        {
            " READ_FILE ",
            "LIST_FILES",
        }
    )

    assert validator.allowed_tools == frozenset(
        {
            "read_file",
            "list_files",
        }
    )


def test_invalid_allowed_tools_container_is_rejected():
    with pytest.raises(
        TypeError,
        match="allowed_tools must be a set or frozenset",
    ):
        ToolAgentInstructionValidator(
            ["read_file"]
        )


def test_non_instruction_is_rejected():
    validator = ToolAgentInstructionValidator(TOOLS)

    with pytest.raises(
        TypeError,
        match="instruction must be a ModelToolInstruction",
    ):
        validator.validate("not an instruction")


def test_validator_preserves_raw_response():
    validator = ToolAgentInstructionValidator(TOOLS)

    raw = json.dumps(
        {
            "action": "continue",
            "reason": "Inspect the file.",
            "tool_name": "read_file",
        }
    )

    parsed = ToolAgentModelParser().parse(raw)
    result = validator.validate(parsed)

    assert result.instruction.raw_response == raw


def test_validator_does_not_execute_tools():
    calls = []

    validator = ToolAgentInstructionValidator(TOOLS)

    result = validator.validate(
        instruction(
            action="continue",
            tool_name="delete_file",
        )
    )

    assert result.instruction.tool_name == "delete_file"
    assert calls == []
