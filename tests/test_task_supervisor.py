import pytest

from core.task_supervisor import (
    TaskExecution,
    TaskSupervisor,
)


def test_create_task():
    supervisor = TaskSupervisor(max_attempts=3)

    result = supervisor.create("task-1")

    assert isinstance(result, TaskExecution)
    assert result.task_id == "task-1"
    assert result.status == "created"
    assert result.attempt == 0
    assert result.max_attempts == 3
    assert result.success is None


def test_start_task_increments_attempt():
    supervisor = TaskSupervisor(max_attempts=3)

    supervisor.create("task-1")

    result = supervisor.start("task-1")

    assert result.status == "running"
    assert result.attempt == 1
    assert result.success is None


def test_retry_moves_task_to_retrying_without_incrementing_attempt():
    supervisor = TaskSupervisor(max_attempts=3)

    supervisor.create("task-1")
    supervisor.start("task-1")

    result = supervisor.retry(
        "task-1",
        "verification failed",
    )

    assert result.status == "retrying"
    assert result.attempt == 1
    assert result.success is None
    assert result.reason == "verification failed"


def test_retry_can_start_next_attempt():
    supervisor = TaskSupervisor(max_attempts=3)

    supervisor.create("task-1")
    supervisor.start("task-1")
    supervisor.retry("task-1", "retry required")

    result = supervisor.start("task-1")

    assert result.status == "running"
    assert result.attempt == 2


def test_complete_task():
    supervisor = TaskSupervisor()

    supervisor.create("task-1")
    supervisor.start("task-1")

    result = supervisor.complete("task-1")

    assert result.status == "completed"
    assert result.success is True
    assert result.attempt == 1


def test_fail_task():
    supervisor = TaskSupervisor()

    supervisor.create("task-1")
    supervisor.start("task-1")

    result = supervisor.fail(
        "task-1",
        "agent failed",
    )

    assert result.status == "failed"
    assert result.success is False
    assert result.reason == "agent failed"


def test_stop_task():
    supervisor = TaskSupervisor()

    supervisor.create("task-1")

    result = supervisor.stop(
        "task-1",
        "user stopped task",
    )

    assert result.status == "stopped"
    assert result.success is False


def test_retry_at_limit_transitions_to_failed():
    supervisor = TaskSupervisor(max_attempts=1)

    supervisor.create("task-1")
    supervisor.start("task-1")

    result = supervisor.retry(
        "task-1",
        "another retry requested",
    )

    assert result.status == "failed"
    assert result.success is False
    assert result.attempt == 1
    assert "maximum" in result.reason


def test_cannot_complete_created_task():
    supervisor = TaskSupervisor()

    supervisor.create("task-1")

    with pytest.raises(ValueError):
        supervisor.complete("task-1")


def test_cannot_fail_created_task():
    supervisor = TaskSupervisor()

    supervisor.create("task-1")

    with pytest.raises(ValueError):
        supervisor.fail(
            "task-1",
            "failed",
        )


def test_cannot_retry_created_task():
    supervisor = TaskSupervisor()

    supervisor.create("task-1")

    with pytest.raises(ValueError):
        supervisor.retry(
            "task-1",
            "retry",
        )


def test_cannot_start_completed_task():
    supervisor = TaskSupervisor()

    supervisor.create("task-1")
    supervisor.start("task-1")
    supervisor.complete("task-1")

    with pytest.raises(ValueError):
        supervisor.start("task-1")


def test_cannot_start_failed_task():
    supervisor = TaskSupervisor()

    supervisor.create("task-1")
    supervisor.start("task-1")
    supervisor.fail("task-1", "failed")

    with pytest.raises(ValueError):
        supervisor.start("task-1")


def test_stop_from_retrying_is_allowed():
    supervisor = TaskSupervisor()

    supervisor.create("task-1")
    supervisor.start("task-1")
    supervisor.retry("task-1", "retry")

    result = supervisor.stop(
        "task-1",
        "shutdown",
    )

    assert result.status == "stopped"


def test_duplicate_task_is_rejected():
    supervisor = TaskSupervisor()

    supervisor.create("task-1")

    with pytest.raises(
        ValueError,
        match="task already exists",
    ):
        supervisor.create("task-1")


def test_unknown_task_is_rejected():
    supervisor = TaskSupervisor()

    with pytest.raises(
        KeyError,
        match="unknown task",
    ):
        supervisor.start("missing")


def test_empty_task_id_is_rejected():
    supervisor = TaskSupervisor()

    with pytest.raises(
        ValueError,
        match="task_id must not be empty",
    ):
        supervisor.create(" ")


def test_empty_reason_is_rejected():
    supervisor = TaskSupervisor()

    supervisor.create("task-1")
    supervisor.start("task-1")

    with pytest.raises(
        ValueError,
        match="reason must not be empty",
    ):
        supervisor.fail("task-1", " ")


def test_invalid_max_attempts_is_rejected():
    with pytest.raises(
        ValueError,
        match="max_attempts must be >= 1",
    ):
        TaskSupervisor(max_attempts=0)


def test_all_returns_sorted_tasks():
    supervisor = TaskSupervisor()

    supervisor.create("task-b")
    supervisor.create("task-a")

    result = supervisor.all()

    assert [item.task_id for item in result] == [
        "task-a",
        "task-b",
    ]


def test_get_returns_current_task_state():
    supervisor = TaskSupervisor()

    supervisor.create("task-1")
    supervisor.start("task-1")

    result = supervisor.get("task-1")

    assert result is not None
    assert result.status == "running"
    assert result.attempt == 1


def test_missing_task_returns_none():
    supervisor = TaskSupervisor()

    assert supervisor.get("missing") is None


def test_clear_removes_all_tasks():
    supervisor = TaskSupervisor()

    supervisor.create("task-a")
    supervisor.create("task-b")

    supervisor.clear()

    assert supervisor.all() == ()


def test_lifecycle_is_deterministic():
    supervisor = TaskSupervisor(max_attempts=2)

    supervisor.create("task-1")
    first = supervisor.start("task-1")
    retry = supervisor.retry("task-1", "retry")
    second = supervisor.start("task-1")
    final = supervisor.complete("task-1")

    assert [item.status for item in (
        first,
        retry,
        second,
        final,
    )] == [
        "running",
        "retrying",
        "running",
        "completed",
    ]
