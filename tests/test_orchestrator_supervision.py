import pytest

from core.orchestrator import Orchestrator
from core.task_supervisor import TaskExecution


def make_orchestrator():
    orchestrator = object.__new__(Orchestrator)

    def fake_handle(
        user_input,
        **kwargs,
    ):
        return f"handled: {user_input}"

    orchestrator.handle = fake_handle

    return orchestrator


def test_handle_supervised_returns_response_and_completed_task():
    orchestrator = make_orchestrator()

    response, execution = orchestrator.handle_supervised(
        "hello",
        task_id="task-1",
    )

    assert response == "handled: hello"
    assert isinstance(execution, TaskExecution)
    assert execution.task_id == "task-1"
    assert execution.status == "completed"
    assert execution.attempt == 1
    assert execution.success is True


def test_handle_supervised_generates_task_id():
    orchestrator = make_orchestrator()

    response, execution = orchestrator.handle_supervised(
        "hello",
    )

    assert response == "handled: hello"
    assert execution.task_id.startswith("task-")
    assert execution.status == "completed"


def test_handle_supervised_marks_task_failed_on_exception():
    orchestrator = object.__new__(Orchestrator)

    def failing_handle(
        user_input,
        **kwargs,
    ):
        raise ValueError("bad request")

    orchestrator.handle = failing_handle

    with pytest.raises(
        RuntimeError,
        match="MyAI task",
    ):
        orchestrator.handle_supervised(
            "broken",
            task_id="task-fail",
        )


def test_handle_supervised_preserves_handle_arguments():
    orchestrator = object.__new__(Orchestrator)

    captured = {}

    def fake_handle(
        user_input,
        **kwargs,
    ):
        captured["user_input"] = user_input
        captured["kwargs"] = kwargs
        return "ok"

    orchestrator.handle = fake_handle

    signals = ["signal"]

    response, execution = orchestrator.handle_supervised(
        "request",
        task_id="task-args",
        learning_signals=signals,
        utility_by_strategy={"property": 90.0},
        baseline_score_by_strategy={"property": 70.0},
        task_family="debugging",
        allow_cross_task=True,
    )

    assert response == "ok"
    assert execution.success is True

    assert captured["user_input"] == "request"
    assert captured["kwargs"] == {
        "learning_signals": signals,
        "utility_by_strategy": {"property": 90.0},
        "baseline_score_by_strategy": {"property": 70.0},
        "task_family": "debugging",
        "allow_cross_task": True,
    }


def test_existing_handle_contract_remains_string_returning():
    orchestrator = make_orchestrator()

    result = orchestrator.handle("hello")

    assert isinstance(result, str)
    assert result == "handled: hello"
