import pytest

from core.tool_agent_context import ToolAgentContextBuilder
from core.tool_agent_prompt import ToolAgentPromptBuilder
from core.tool_agent_session import ToolAgentSession
from core.tool_decision_engine import ToolDecisionResult
from core.tool_plan_executor import ToolExecutionPlanResult
from core.tool_planner import ToolDecision
from tools.base import ToolResult


def make_decision(tool_name):
    return ToolDecisionResult(
        decision=ToolDecision(
            tool_name=tool_name,
            reason="test",
            confidence=1.0,
        ),
        arguments={},
    )


def successful_plan(
    tool_name="read_file",
    result="VALUE = 42\n",
):
    return ToolExecutionPlanResult(
        decision=make_decision(tool_name),
        execution=ToolResult(
            tool_name=tool_name,
            success=True,
            result=result,
        ),
        executed=True,
    )


def failed_plan():
    return ToolExecutionPlanResult(
        decision=make_decision("read_file"),
        execution=ToolResult(
            tool_name="read_file",
            success=False,
            result=None,
            error="File does not exist.",
        ),
        executed=True,
    )


def build_context(executor, request):
    session = ToolAgentSession(executor)
    session.step(request)
    return ToolAgentContextBuilder().build(session)


def test_prompt_contains_system_instructions():
    context = build_context(
        lambda request: successful_plan(),
        "Read config.py",
    )

    prompt = ToolAgentPromptBuilder().build(
        "Read config.py",
        context,
    )

    assert "You are MyAI's tool-reasoning component." in prompt
    assert "Do not invent tool results." in prompt


def test_prompt_contains_user_request():
    request = "Read config.py"

    context = build_context(
        lambda value: successful_plan(),
        request,
    )

    prompt = ToolAgentPromptBuilder().build(
        request,
        context,
    )

    assert "USER REQUEST:" in prompt
    assert request in prompt


def test_prompt_contains_successful_tool_context():
    request = "Read config.py"

    context = build_context(
        lambda value: successful_plan(),
        request,
    )

    prompt = ToolAgentPromptBuilder().build(
        request,
        context,
    )

    assert "TOOL EXECUTION CONTEXT:" in prompt
    assert "step_1.request: Read config.py" in prompt
    assert "step_1.tool_name: read_file" in prompt
    assert "step_1.success: True" in prompt
    assert "step_1.result: VALUE = 42" in prompt
    assert "step_1.next_action: complete" in prompt


def test_prompt_contains_failed_tool_context():
    request = "Read missing.py"

    context = build_context(
        lambda value: failed_plan(),
        request,
    )

    prompt = ToolAgentPromptBuilder().build(
        request,
        context,
    )

    assert "step_1.success: False" in prompt
    assert "step_1.error: File does not exist." in prompt
    assert "step_1.next_action: stop" in prompt


def test_prompt_contains_continuation_state():
    request = "Read config.py and then verify it"

    context = build_context(
        lambda value: successful_plan(),
        request,
    )

    prompt = ToolAgentPromptBuilder().build(
        request,
        context,
    )

    assert "status: active" in prompt
    assert "should_continue: True" in prompt
    assert "step_1.next_action: continue" in prompt


def test_empty_context_can_be_formatted():
    session = ToolAgentSession(lambda request: successful_plan())
    context = ToolAgentContextBuilder().build(session)

    prompt = ToolAgentPromptBuilder().build(
        "Read config.py",
        context,
    )

    assert "USER REQUEST:" in prompt
    assert "Read config.py" in prompt
    assert "status: active" in prompt
    assert "step_count: 0" in prompt


def test_prompt_builder_does_not_modify_context():
    request = "Read config.py"

    context = build_context(
        lambda value: successful_plan(),
        request,
    )

    before = context

    ToolAgentPromptBuilder().build(
        request,
        context,
    )

    assert context == before


def test_prompt_builder_does_not_execute_tools():
    calls = []

    def executor(request):
        calls.append(request)
        return successful_plan()

    session = ToolAgentSession(executor)
    context = ToolAgentContextBuilder().build(session)

    ToolAgentPromptBuilder().build(
        "Read config.py",
        context,
    )

    assert calls == []


def test_non_string_request_is_rejected():
    session = ToolAgentSession(lambda request: successful_plan())
    context = ToolAgentContextBuilder().build(session)

    with pytest.raises(
        TypeError,
        match="request must be a string",
    ):
        ToolAgentPromptBuilder().build(
            123,
            context,
        )
