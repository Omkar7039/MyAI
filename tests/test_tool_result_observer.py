from core.tool_decision_engine import ToolDecisionResult
from core.tool_plan_executor import ToolExecutionPlanResult
from core.tool_planner import ToolDecision
from core.tool_result_observer import ToolObservation, ToolResultObserver
from tools.base import ToolResult


def make_decision(tool_name=None, arguments=None):
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
        arguments=arguments or {},
    )


def test_successful_read_file_observation():
    plan = ToolExecutionPlanResult(
        decision=make_decision(
            "read_file",
            {"path": "config.py"},
        ),
        execution=ToolResult(
            tool_name="read_file",
            success=True,
            result="VALUE = 42\n",
        ),
        executed=True,
    )

    observation = ToolResultObserver().observe(plan)

    assert isinstance(observation, ToolObservation)
    assert observation.tool_name == "read_file"
    assert observation.success is True
    assert observation.result == "VALUE = 42\n"
    assert observation.error is None
    assert observation.executed is True


def test_successful_list_files_observation():
    result = {
        "path": "src",
        "entries": ["main.py", "utils.py"],
    }

    plan = ToolExecutionPlanResult(
        decision=make_decision(
            "list_files",
            {"path": "src"},
        ),
        execution=ToolResult(
            tool_name="list_files",
            success=True,
            result=result,
        ),
        executed=True,
    )

    observation = ToolResultObserver().observe(plan)

    assert observation.tool_name == "list_files"
    assert observation.success is True
    assert observation.result == result
    assert observation.error is None
    assert observation.executed is True


def test_failed_tool_observation():
    plan = ToolExecutionPlanResult(
        decision=make_decision(
            "read_file",
            {"path": "missing.py"},
        ),
        execution=ToolResult(
            tool_name="read_file",
            success=False,
            result=None,
            error="File does not exist.",
        ),
        executed=True,
    )

    observation = ToolResultObserver().observe(plan)

    assert observation.tool_name == "read_file"
    assert observation.success is False
    assert observation.result is None
    assert observation.error == "File does not exist."
    assert observation.executed is True


def test_permission_blocked_tool_observation():
    plan = ToolExecutionPlanResult(
        decision=make_decision(
            "delete_file",
            {"path": "important.txt"},
        ),
        execution=None,
        executed=False,
    )

    observation = ToolResultObserver().observe(plan)

    assert observation.tool_name == "delete_file"
    assert observation.success is False
    assert observation.result is None
    assert observation.error is None
    assert observation.executed is False


def test_unknown_request_observation():
    plan = ToolExecutionPlanResult(
        decision=make_decision(),
        execution=None,
        executed=False,
    )

    observation = ToolResultObserver().observe(plan)

    assert observation.tool_name is None
    assert observation.success is False
    assert observation.result is None
    assert observation.error is None
    assert observation.executed is False


def test_observer_does_not_execute_tools():
    plan = ToolExecutionPlanResult(
        decision=make_decision(
            "read_file",
            {"path": "config.py"},
        ),
        execution=None,
        executed=False,
    )

    observation = ToolResultObserver().observe(plan)

    assert observation.executed is False
