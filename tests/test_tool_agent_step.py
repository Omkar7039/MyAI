from dataclasses import dataclass

from core.tool_agent_step import ToolAgentStep, ToolAgentStepResult
from core.tool_decision_engine import ToolDecisionResult
from core.tool_next_decision import NextDecision
from core.tool_plan_executor import ToolExecutionPlanResult
from core.tool_planner import ToolDecision
from core.tool_result_observer import ToolObservation
from tools.base import ToolResult


def make_decision(tool_name=None):
    if tool_name is None:
        return ToolDecisionResult(
            decision=None,
            arguments=None,
        )

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


def failed_plan(tool_name="read_file"):
    return ToolExecutionPlanResult(
        decision=make_decision(tool_name),
        execution=ToolResult(
            tool_name=tool_name,
            success=False,
            result=None,
            error="tool failed",
        ),
        executed=True,
    )


def not_executed_plan(tool_name=None):
    return ToolExecutionPlanResult(
        decision=make_decision(tool_name),
        execution=None,
        executed=False,
    )


def test_single_step_success():
    calls = []

    def executor(request):
        calls.append(request)
        return successful_plan()

    result = ToolAgentStep(executor).run(
        "Read config.py",
    )

    assert isinstance(result, ToolAgentStepResult)
    assert calls == ["Read config.py"]
    assert result.observation.tool_name == "read_file"
    assert result.observation.success is True
    assert result.observation.result == "VALUE = 42\n"
    assert result.next_decision.action == "complete"


def test_single_step_follow_up_continues():
    calls = []

    def executor(request):
        calls.append(request)
        return successful_plan()

    result = ToolAgentStep(executor).run(
        "Read config.py and then verify the value",
    )

    assert calls == ["Read config.py and then verify the value"]
    assert result.observation.success is True
    assert result.next_decision.action == "continue"


def test_single_step_failure_stops():
    calls = []

    def executor(request):
        calls.append(request)
        return failed_plan()

    result = ToolAgentStep(executor).run(
        "Read missing.py",
    )

    assert calls == ["Read missing.py"]
    assert result.observation.success is False
    assert result.observation.error == "tool failed"
    assert result.next_decision.action == "stop"


def test_single_step_not_executed_stops():
    calls = []

    def executor(request):
        calls.append(request)
        return not_executed_plan("delete_file")

    result = ToolAgentStep(executor).run(
        "Delete important.txt",
    )

    assert calls == ["Delete important.txt"]
    assert result.observation.executed is False
    assert result.next_decision.action == "stop"


def test_single_step_unknown_request_stops():
    calls = []

    def executor(request):
        calls.append(request)
        return not_executed_plan()

    result = ToolAgentStep(executor).run(
        "Tell me something interesting",
    )

    assert calls == ["Tell me something interesting"]
    assert result.observation.tool_name is None
    assert result.next_decision.action == "stop"


def test_executor_is_called_exactly_once():
    count = 0

    def executor(request):
        nonlocal count
        count += 1
        return successful_plan()

    result = ToolAgentStep(executor).run(
        "Read config.py",
    )

    assert result.observation.success is True
    assert count == 1
