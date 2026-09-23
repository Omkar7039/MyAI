from core.tool_agent_context import (
    ToolAgentContext,
    ToolAgentContextBuilder,
    ToolAgentContextEntry,
)
from core.tool_agent_session import ToolAgentSession
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


def successful_plan(tool_name="read_file", result="VALUE = 42\n"):
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


def test_empty_session_builds_empty_context():
    def executor(request):
        return successful_plan()

    session = ToolAgentSession(executor)
    context = ToolAgentContextBuilder().build(session)

    assert isinstance(context, ToolAgentContext)
    assert context.entries == ()
    assert context.step_count == 0
    assert context.max_steps == 10
    assert context.status == "active"
    assert context.should_continue is False


def test_successful_step_becomes_context_entry():
    def executor(request):
        return successful_plan()

    session = ToolAgentSession(executor)
    session.step("Read config.py")

    context = ToolAgentContextBuilder().build(session)

    assert len(context.entries) == 1

    entry = context.entries[0]

    assert isinstance(entry, ToolAgentContextEntry)
    assert entry.request == "Read config.py"
    assert entry.tool_name == "read_file"
    assert entry.success is True
    assert entry.result == "VALUE = 42\n"
    assert entry.error is None
    assert entry.executed is True
    assert entry.next_action == "complete"
    assert "completed successfully" in entry.next_reason


def test_failed_step_preserves_error():
    def executor(request):
        return failed_plan()

    session = ToolAgentSession(executor)
    session.step("Read missing.py")

    context = ToolAgentContextBuilder().build(session)

    entry = context.entries[0]

    assert entry.request == "Read missing.py"
    assert entry.tool_name == "read_file"
    assert entry.success is False
    assert entry.result is None
    assert entry.error == "tool failed"
    assert entry.executed is True
    assert entry.next_action == "stop"
    assert "failed" in entry.next_reason
    assert context.status == "stopped"
    assert context.should_continue is False


def test_multiple_steps_preserve_order():
    def executor(request):
        return successful_plan(
            result=f"result for {request}",
        )

    session = ToolAgentSession(executor)

    session.step("Read config.py")
    session.step("Read settings.py")

    context = ToolAgentContextBuilder().build(session)

    assert [entry.request for entry in context.entries] == [
        "Read config.py",
        "Read settings.py",
    ]

    assert [entry.result for entry in context.entries] == [
        "result for Read config.py",
        "result for Read settings.py",
    ]

    assert context.step_count == 2


def test_context_is_immutable():
    def executor(request):
        return successful_plan()

    session = ToolAgentSession(executor)
    session.step("Read config.py")

    context = ToolAgentContextBuilder().build(session)

    try:
        context.step_count = 99
        assert False, "Context should be immutable"
    except AttributeError:
        pass


def test_context_snapshot_is_independent_from_later_session_steps():
    def executor(request):
        return successful_plan()

    session = ToolAgentSession(executor)

    session.step("Read config.py")
    context = ToolAgentContextBuilder().build(session)

    session.step("Read settings.py")

    assert len(context.entries) == 1
    assert context.step_count == 1


def test_continuation_state_is_preserved():
    def executor(request):
        return successful_plan()

    session = ToolAgentSession(executor)

    session.step("Read config.py and then verify it")

    context = ToolAgentContextBuilder().build(session)

    assert len(context.entries) == 1
    assert context.status == "active"
    assert context.should_continue is True


def test_continuation_decision_is_preserved_in_context_entry():
    def executor(request):
        return successful_plan()

    session = ToolAgentSession(executor)

    session.step("Read config.py and then verify it")

    context = ToolAgentContextBuilder().build(session)

    entry = context.entries[0]

    assert entry.next_action == "continue"
    assert "follow-up" in entry.next_reason


def test_context_entries_preserve_decision_metadata_in_order():
    def executor(request):
        return successful_plan(result=request)

    session = ToolAgentSession(executor)

    session.step("Read config.py")
    session.step("Read settings.py")

    context = ToolAgentContextBuilder().build(session)

    assert [
        entry.next_action
        for entry in context.entries
    ] == [
        "complete",
        "complete",
    ]


def test_context_decision_metadata_is_immutable():
    def executor(request):
        return successful_plan()

    session = ToolAgentSession(executor)
    session.step("Read config.py")

    context = ToolAgentContextBuilder().build(session)

    try:
        context.entries[0].next_action = "continue"
        assert False, "Context entries should be immutable"
    except AttributeError:
        pass
