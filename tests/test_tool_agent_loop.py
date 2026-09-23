from core.tool_agent_loop import ToolAgentLoop
from core.tool_agent_step import ToolAgentStep
from core.tool_next_decision import NextDecision
from core.tool_plan_executor import ToolExecutionPlanResult
from core.tool_decision_engine import ToolDecisionResult
from core.tool_planner import ToolDecision
from tools.base import ToolResult


def plan(action_tool="read_file"):
    return ToolExecutionPlanResult(
        decision=ToolDecisionResult(
            decision=ToolDecision(
                tool_name=action_tool,
                reason="test",
                confidence=1.0,
            ),
            arguments={},
        ),
        execution=ToolResult(
            tool_name=action_tool,
            success=True,
            result="ok",
        ),
        executed=True,
    )


def test_loop_completes_after_one_step():
    calls = []

    def executor(request):
        calls.append(request)
        return plan()

    loop = ToolAgentLoop(
        ToolAgentStep(executor),
    )

    result = loop.run("Read config.py")

    assert len(result.steps) == 1
    assert result.completed is True
    assert result.stopped is False
    assert result.max_steps_reached is False
    assert calls == ["Read config.py"]


def test_loop_stops_when_step_stops():
    class StopStep:
        def run(self, request):
            return type(
                "Result",
                (),
                {
                    "next_decision": NextDecision(
                        action="stop",
                        reason="test",
                    ),
                },
            )()

    result = ToolAgentLoop(StopStep()).run("test")

    assert len(result.steps) == 1
    assert result.stopped is True
    assert result.completed is False


def test_loop_enforces_max_steps():
    calls = []

    class ContinueStep:
        def run(self, request):
            calls.append(request)
            return type(
                "Result",
                (),
                {
                    "next_decision": NextDecision(
                        action="continue",
                        reason="test",
                    ),
                },
            )()

    result = ToolAgentLoop(
        ContinueStep(),
        max_steps=3,
    ).run("test")

    assert len(result.steps) == 3
    assert len(calls) == 3
    assert result.max_steps_reached is True
    assert result.completed is False


def test_loop_rejects_invalid_max_steps():
    try:
        ToolAgentLoop(
            ToolAgentStep(lambda request: plan()),
            max_steps=0,
        )
    except ValueError as exc:
        assert str(exc) == "max_steps must be at least 1"
    else:
        raise AssertionError("Expected ValueError")
