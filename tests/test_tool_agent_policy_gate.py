import json

import pytest

from core.tool_agent_instruction_validator import (
    ToolAgentInstructionValidator,
    ValidatedToolInstruction,
)
from core.tool_agent_model_parser import ToolAgentModelParser
from core.tool_agent_policy_gate import (
    PolicyCheckedToolInstruction,
    ToolAgentPolicyGate,
)


TOOLS = {
    "read_file",
    "write_file",
    "delete_file",
    "execute_code",
}


def parse_instruction(
    action="continue",
    reason="Need another step.",
    tool_name="read_file",
):
    response = json.dumps(
        {
            "action": action,
            "reason": reason,
            "tool_name": tool_name,
        }
    )

    parsed = ToolAgentModelParser().parse(response)

    return ToolAgentInstructionValidator(TOOLS).validate(parsed)


def test_allowed_tool_passes_policy_gate():
    calls = []

    def checker(tool_name):
        calls.append(tool_name)
        return True

    gate = ToolAgentPolicyGate(checker)

    result = gate.check(
        parse_instruction(
            action="continue",
            tool_name="read_file",
        )
    )

    assert isinstance(result, PolicyCheckedToolInstruction)
    assert result.allowed is True
    assert result.instruction.instruction.tool_name == "read_file"
    assert calls == ["read_file"]


def test_blocked_tool_fails_policy_gate():
    calls = []

    def checker(tool_name):
        calls.append(tool_name)
        return False

    gate = ToolAgentPolicyGate(checker)

    result = gate.check(
        parse_instruction(
            action="continue",
            tool_name="delete_file",
        )
    )

    assert result.allowed is False
    assert result.instruction.instruction.tool_name == "delete_file"
    assert "blocked" in result.reason
    assert calls == ["delete_file"]


def test_complete_does_not_call_permission_checker():
    calls = []

    def checker(tool_name):
        calls.append(tool_name)
        return False

    gate = ToolAgentPolicyGate(checker)

    result = gate.check(
        parse_instruction(
            action="complete",
            reason="Task is complete.",
            tool_name=None,
        )
    )

    assert result.allowed is True
    assert result.reason == "No tool execution is requested."
    assert calls == []


def test_stop_does_not_call_permission_checker():
    calls = []

    def checker(tool_name):
        calls.append(tool_name)
        return False

    gate = ToolAgentPolicyGate(checker)

    result = gate.check(
        parse_instruction(
            action="stop",
            reason="Stopping.",
            tool_name=None,
        )
    )

    assert result.allowed is True
    assert result.reason == "No tool execution is requested."
    assert calls == []


def test_checker_is_not_called_without_tool_name():
    calls = []

    def checker(tool_name):
        calls.append(tool_name)
        return False

    gate = ToolAgentPolicyGate(checker)

    raw = parse_instruction(
        action="continue",
        reason="Need another step.",
        tool_name="read_file",
    )

    instruction = ValidatedToolInstruction(
        instruction=type(raw.instruction)(
            action="continue",
            reason=raw.instruction.reason,
            tool_name=None,
            raw_response=raw.instruction.raw_response,
        )
    )

    result = gate.check(instruction)

    assert result.allowed is False
    assert result.reason == "Tool execution requires a tool name."
    assert calls == []


def test_non_callable_checker_is_rejected():
    with pytest.raises(
        TypeError,
        match="permission_checker must be callable",
    ):
        ToolAgentPolicyGate("not callable")


def test_non_validated_instruction_is_rejected():
    gate = ToolAgentPolicyGate(lambda tool_name: True)

    with pytest.raises(
        TypeError,
        match="instruction must be a ValidatedToolInstruction",
    ):
        gate.check("not validated")


def test_permission_checker_receives_normalized_tool_name():
    calls = []

    def checker(tool_name):
        calls.append(tool_name)
        return True

    gate = ToolAgentPolicyGate(checker)

    result = gate.check(
        parse_instruction(
            action="continue",
            tool_name=" READ_FILE ",
        )
    )

    assert result.allowed is True
    assert calls == ["read_file"]


def test_policy_result_preserves_validated_instruction():
    gate = ToolAgentPolicyGate(lambda tool_name: True)

    instruction = parse_instruction(
        action="continue",
        tool_name="read_file",
    )

    result = gate.check(instruction)

    assert result.instruction is instruction


def test_policy_gate_does_not_execute_tools():
    tool_calls = []

    gate = ToolAgentPolicyGate(lambda tool_name: True)

    result = gate.check(
        parse_instruction(
            action="continue",
            tool_name="delete_file",
        )
    )

    assert result.allowed is True
    assert tool_calls == []


def test_block_reason_identifies_tool():
    gate = ToolAgentPolicyGate(lambda tool_name: False)

    result = gate.check(
        parse_instruction(
            action="continue",
            tool_name="execute_code",
        )
    )

    assert result.allowed is False
    assert "execute_code" in result.reason


def test_allow_reason_identifies_tool():
    gate = ToolAgentPolicyGate(lambda tool_name: True)

    result = gate.check(
        parse_instruction(
            action="continue",
            tool_name="read_file",
        )
    )

    assert result.allowed is True
    assert "read_file" in result.reason
