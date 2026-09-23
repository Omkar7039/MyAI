import pytest

from core.tool_agent_session import (
    ToolAgentSession,
    ToolAgentSessionSnapshot,
)
from core.tool_plan_executor import ToolExecutionPlanResult
from core.tool_decision_engine import ToolDecisionResult
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


def successful_plan(tool_name="read_file"):
    return ToolExecutionPlanResult(
        decision=make_decision(tool_name),
        execution=ToolResult(
            tool_name=tool_name,
            success=True,
            result="VALUE = 42\n",
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


def continuation_plan():
    return successful_plan("read_file")


def test_session_starts_empty():
    calls = []

    def executor(request):
        calls.append(request)
        return successful_plan()

    session = ToolAgentSession(executor)

    assert session.step_count == 0
    assert session.max_steps == 10
    assert session.history == ()
    assert session.last_result is None
    assert session.should_continue is False
    assert calls == []


def test_session_executes_one_explicit_step():
    calls = []

    def executor(request):
        calls.append(request)
        return successful_plan()

    session = ToolAgentSession(executor)

    result = session.step("Read config.py")

    assert calls == ["Read config.py"]
    assert session.step_count == 1
    assert len(session.history) == 1
    assert session.last_result is result
    assert result.observation.success is True


def test_session_never_automatically_executes_follow_up():
    calls = []

    def executor(request):
        calls.append(request)
        return successful_plan()

    session = ToolAgentSession(executor)

    result = session.step("Read config.py and then verify it")

    assert result.next_decision.action == "continue"
    assert calls == ["Read config.py and then verify it"]
    assert len(calls) == 1
    assert session.step_count == 1


def test_session_history_preserves_multiple_explicit_steps():
    calls = []

    def executor(request):
        calls.append(request)
        return successful_plan()

    session = ToolAgentSession(executor)

    first = session.step("Read config.py")
    second = session.step("Read settings.py")

    assert calls == [
        "Read config.py",
        "Read settings.py",
    ]
    assert session.step_count == 2
    assert session.history == (first, second)
    assert session.last_result is second


def test_session_respects_max_steps():
    calls = []

    def executor(request):
        calls.append(request)
        return successful_plan()

    session = ToolAgentSession(
        executor,
        max_steps=2,
    )

    session.step("Read config.py")
    session.step("Read settings.py")

    with pytest.raises(
        RuntimeError,
        match="Maximum tool-agent session steps reached",
    ):
        session.step("Read third.py")

    assert calls == [
        "Read config.py",
        "Read settings.py",
    ]
    assert session.step_count == 2


def test_should_continue_reflects_last_decision():
    calls = []

    def executor(request):
        calls.append(request)
        return continuation_plan()

    session = ToolAgentSession(executor)

    result = session.step(
        "Read config.py and then verify the value",
    )

    assert result.next_decision.action == "continue"
    assert session.should_continue is True


def test_should_continue_becomes_false_at_max_steps():
    calls = []

    def executor(request):
        calls.append(request)
        return continuation_plan()

    session = ToolAgentSession(
        executor,
        max_steps=1,
    )

    session.step(
        "Read config.py and then verify the value",
    )

    assert session.step_count == 1
    assert session.should_continue is False


def test_snapshot_returns_stable_session_state():
    calls = []

    def executor(request):
        calls.append(request)
        return successful_plan()

    session = ToolAgentSession(
        executor,
        max_steps=3,
    )

    result = session.step("Read config.py")
    snapshot = session.snapshot()

    assert isinstance(snapshot, ToolAgentSessionSnapshot)
    assert snapshot.step_count == 1
    assert snapshot.max_steps == 3
    assert snapshot.should_continue is False
    assert snapshot.last_result is result


def test_reset_clears_session_history():
    calls = []

    def executor(request):
        calls.append(request)
        return successful_plan()

    session = ToolAgentSession(executor)

    session.step("Read config.py")
    assert session.step_count == 1

    session.reset()

    assert session.step_count == 0
    assert session.history == ()
    assert session.last_result is None
    assert session.should_continue is False


def test_session_request_history_preserves_explicit_steps():
    calls = []

    def executor(request):
        calls.append(request)
        return successful_plan()

    session = ToolAgentSession(executor)

    session.step("Read config.py")
    session.step("Read settings.py")

    assert session.request_history == (
        "Read config.py",
        "Read settings.py",
    )


def test_session_last_request_returns_latest_request():
    def executor(request):
        return successful_plan()

    session = ToolAgentSession(executor)

    assert session.last_request is None

    session.step("Read config.py")

    assert session.last_request == "Read config.py"

    session.step("Read settings.py")

    assert session.last_request == "Read settings.py"


def test_session_request_history_matches_result_history():
    def executor(request):
        return successful_plan()

    session = ToolAgentSession(executor)

    session.step("first")
    session.step("second")

    assert len(session.request_history) == len(session.history)


def test_failed_explicit_step_is_recorded_in_request_history():
    def executor(request):
        return failed_plan()

    session = ToolAgentSession(executor)

    session.step("Read missing.py")

    assert session.request_history == ("Read missing.py",)
    assert session.last_request == "Read missing.py"


def test_max_step_rejection_does_not_add_request_to_history():
    calls = []

    def executor(request):
        calls.append(request)
        return successful_plan()

    session = ToolAgentSession(
        executor,
        max_steps=1,
    )

    session.step("first")

    try:
        session.step("second")
    except RuntimeError:
        pass

    assert session.request_history == ("first",)
    assert calls == ["first"]


def test_reset_clears_request_history():
    def executor(request):
        return successful_plan()

    session = ToolAgentSession(executor)

    session.step("Read config.py")
    assert session.request_history == ("Read config.py",)

    session.reset()

    assert session.request_history == ()
    assert session.last_request is None


def test_session_status_is_active_when_empty():
    def executor(request):
        return successful_plan()

    session = ToolAgentSession(executor)

    assert session.status == "active"


def test_session_status_is_completed_after_successful_completion():
    def executor(request):
        return successful_plan()

    session = ToolAgentSession(executor)

    session.step("Read config.py")

    assert session.status == "completed"


def test_session_status_is_active_after_continuation_request():
    def executor(request):
        return successful_plan()

    session = ToolAgentSession(executor)

    session.step("Read config.py and then verify it")

    assert session.status == "active"
    assert session.should_continue is True


def test_session_status_is_stopped_after_failed_step():
    def executor(request):
        return failed_plan()

    session = ToolAgentSession(executor)

    session.step("Read missing.py")

    assert session.status == "stopped"
    assert session.should_continue is False


def test_session_status_is_limit_reached_at_max_steps():
    def executor(request):
        return successful_plan()

    session = ToolAgentSession(
        executor,
        max_steps=1,
    )

    session.step("Read config.py")

    assert session.status == "limit_reached"
    assert session.should_continue is False


def test_session_snapshot_contains_status():
    def executor(request):
        return successful_plan()

    session = ToolAgentSession(executor)

    session.step("Read config.py")
    snapshot = session.snapshot()

    assert snapshot.status == "completed"


def test_session_reset_returns_to_active_status():
    def executor(request):
        return successful_plan()

    session = ToolAgentSession(executor)

    session.step("Read config.py")
    assert session.status == "completed"

    session.reset()

    assert session.status == "active"
