from core.tool_agent_context import ToolAgentContextBuilder
from core.tool_agent_context_formatter import ToolAgentContextFormatter
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
            error="tool failed",
        ),
        executed=True,
    )


def build_context(executor):
    session = ToolAgentSession(executor)
    return ToolAgentContextBuilder().build(session)


def test_empty_context_to_dict():
    context = build_context(lambda request: successful_plan())
    formatted = ToolAgentContextFormatter().to_dict(context)

    assert formatted == {
        "entries": [],
        "step_count": 0,
        "max_steps": 10,
        "status": "active",
        "should_continue": False,
    }


def test_successful_context_to_dict():
    def executor(request):
        return successful_plan()

    session = ToolAgentSession(executor)
    session.step("Read config.py")
    context = ToolAgentContextBuilder().build(session)

    formatted = ToolAgentContextFormatter().to_dict(context)

    assert formatted["step_count"] == 1
    assert formatted["status"] == "completed"
    assert formatted["should_continue"] is False
    assert formatted["entries"] == [
        {
            "request": "Read config.py",
            "tool_name": "read_file",
            "success": True,
            "result": "VALUE = 42\n",
            "error": None,
            "executed": True,
            "next_action": "complete",
            "next_reason": "The observed tool execution completed successfully with no explicit follow-up step.",
        }
    ]


def test_failed_context_to_dict():
    def executor(request):
        return failed_plan()

    session = ToolAgentSession(executor)
    session.step("Read missing.py")
    context = ToolAgentContextBuilder().build(session)

    formatted = ToolAgentContextFormatter().to_dict(context)

    assert formatted["status"] == "stopped"
    assert formatted["entries"][0]["success"] is False
    assert formatted["entries"][0]["error"] == "tool failed"
    assert formatted["entries"][0]["result"] is None


def test_multiple_entries_preserve_order():
    def executor(request):
        return successful_plan(result=request)

    session = ToolAgentSession(executor)

    session.step("Read config.py")
    session.step("Read settings.py")

    context = ToolAgentContextBuilder().build(session)
    formatted = ToolAgentContextFormatter().to_dict(context)

    assert [
        entry["request"]
        for entry in formatted["entries"]
    ] == [
        "Read config.py",
        "Read settings.py",
    ]


def test_to_dict_returns_plain_mutable_container():
    def executor(request):
        return successful_plan()

    session = ToolAgentSession(executor)
    session.step("Read config.py")
    context = ToolAgentContextBuilder().build(session)

    formatted = ToolAgentContextFormatter().to_dict(context)

    formatted["entries"].append({"extra": True})

    assert len(context.entries) == 1


def test_to_text_contains_session_metadata():
    context = build_context(lambda request: successful_plan())

    text = ToolAgentContextFormatter().to_text(context)

    assert "status: active" in text
    assert "step_count: 0" in text
    assert "max_steps: 10" in text
    assert "should_continue: False" in text


def test_to_text_contains_tool_observation():
    def executor(request):
        return successful_plan()

    session = ToolAgentSession(executor)
    session.step("Read config.py")
    context = ToolAgentContextBuilder().build(session)

    text = ToolAgentContextFormatter().to_text(context)

    assert "step_1.request: Read config.py" in text
    assert "step_1.tool_name: read_file" in text
    assert "step_1.success: True" in text
    assert "step_1.result: VALUE = 42" in text
    assert "step_1.error: None" in text
    assert "step_1.executed: True" in text
    assert "step_1.next_action: complete" in text
    assert "step_1.next_reason: The observed tool execution completed successfully" in text


def test_continuation_state_is_preserved():
    def executor(request):
        return successful_plan()

    session = ToolAgentSession(executor)
    session.step("Read config.py and then verify it")

    context = ToolAgentContextBuilder().build(session)
    formatted = ToolAgentContextFormatter().to_dict(context)

    assert formatted["status"] == "active"
    assert formatted["should_continue"] is True


def test_formatter_does_not_change_session():
    def executor(request):
        return successful_plan()

    session = ToolAgentSession(executor)
    session.step("Read config.py")

    before = session.snapshot()

    context = ToolAgentContextBuilder().build(session)
    formatter = ToolAgentContextFormatter()

    formatter.to_dict(context)
    formatter.to_text(context)

    after = session.snapshot()

    assert after == before


def test_formatter_preserves_continue_decision():
    def executor(request):
        return successful_plan()

    session = ToolAgentSession(executor)
    session.step("Read config.py and then verify it")

    context = ToolAgentContextBuilder().build(session)
    formatted = ToolAgentContextFormatter().to_dict(context)

    entry = formatted["entries"][0]

    assert entry["next_action"] == "continue"
    assert "follow-up" in entry["next_reason"]


def test_formatter_preserves_decision_metadata_without_changing_context():
    def executor(request):
        return successful_plan()

    session = ToolAgentSession(executor)
    session.step("Read config.py")

    context = ToolAgentContextBuilder().build(session)
    formatter = ToolAgentContextFormatter()

    before = context
    formatter.to_dict(context)
    formatter.to_text(context)

    assert context == before
