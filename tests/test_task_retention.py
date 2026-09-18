import pytest

from core.persistent_task_supervisor import (
    PersistentTaskSupervisor,
)
from core.runtime_state import RuntimeStateStore
from core.task_retention import (
    TaskRetentionManager,
)
from core.task_supervisor import TaskSupervisor


def make_manager(tmp_path, max_terminal_tasks=2):
    store = RuntimeStateStore(
        tmp_path / "runtime.db"
    )

    persistent = PersistentTaskSupervisor(
        store=store,
        supervisor=TaskSupervisor(
            max_attempts=3,
        ),
    )

    return (
        TaskRetentionManager(
            persistent,
            max_terminal_tasks=max_terminal_tasks,
        ),
        persistent,
        store,
    )


def complete(persistent, task_id):
    persistent.create(task_id)
    persistent.start(task_id)
    return persistent.complete(task_id)


def fail(persistent, task_id):
    persistent.create(task_id)
    persistent.start(task_id)
    return persistent.fail(
        task_id,
        "failed",
    )


def stop(persistent, task_id):
    persistent.create(task_id)
    return persistent.stop(
        task_id,
        "stopped",
    )


def test_empty_task_history_is_safe(tmp_path):
    manager, _, _ = make_manager(tmp_path)

    result = manager.run()

    assert result.existing_terminal_tasks == 0
    assert result.retained_terminal_tasks == 0
    assert result.pruned_terminal_tasks == 0
    assert result.active_tasks == 0
    assert result.applied is False


def test_dry_run_does_not_modify_state(tmp_path):
    manager, persistent, _ = make_manager(
        tmp_path,
        max_terminal_tasks=1,
    )

    complete(persistent, "task-1")
    complete(persistent, "task-2")
    persistent.create("task-active")
    persistent.start("task-active")

    before = persistent.all_insertion_order()

    result = manager.run(apply=False)

    after = persistent.all_insertion_order()

    assert result.existing_terminal_tasks == 2
    assert result.retained_terminal_tasks == 1
    assert result.pruned_terminal_tasks == 1
    assert result.active_tasks == 1
    assert result.applied is False
    assert before == after


def test_apply_prunes_oldest_terminal_tasks(tmp_path):
    manager, persistent, _ = make_manager(
        tmp_path,
        max_terminal_tasks=2,
    )

    complete(persistent, "task-1")
    fail(persistent, "task-2")
    stop(persistent, "task-3")

    result = manager.run(apply=True)

    assert result.existing_terminal_tasks == 3
    assert result.retained_terminal_tasks == 2
    assert result.pruned_terminal_tasks == 1
    assert result.applied is True

    tasks = persistent.all_insertion_order()

    assert [task.task_id for task in tasks] == [
        "task-2",
        "task-3",
    ]


def test_active_tasks_are_never_pruned(tmp_path):
    manager, persistent, _ = make_manager(
        tmp_path,
        max_terminal_tasks=0,
    )

    complete(persistent, "task-complete")

    persistent.create("task-active")
    persistent.start("task-active")

    result = manager.run(apply=True)

    assert result.pruned_terminal_tasks == 1
    assert result.active_tasks == 1

    active = persistent.get("task-active")

    assert active is not None
    assert active.status == "running"


def test_retrying_tasks_are_never_pruned(tmp_path):
    manager, persistent, _ = make_manager(
        tmp_path,
        max_terminal_tasks=0,
    )

    complete(persistent, "task-complete")

    persistent.create("task-retrying")
    persistent.start("task-retrying")
    persistent.retry(
        "task-retrying",
        "retry requested",
    )

    manager.run(apply=True)

    retrying = persistent.get("task-retrying")

    assert retrying is not None
    assert retrying.status == "retrying"


def test_zero_retention_removes_all_terminal_tasks(
    tmp_path,
):
    manager, persistent, _ = make_manager(
        tmp_path,
        max_terminal_tasks=0,
    )

    complete(persistent, "task-1")
    fail(persistent, "task-2")
    stop(persistent, "task-3")

    result = manager.run(apply=True)

    assert result.pruned_terminal_tasks == 3
    assert result.retained_terminal_tasks == 0

    assert persistent.all() == ()


def test_other_tasks_survive_retention(tmp_path):
    manager, persistent, _ = make_manager(
        tmp_path,
        max_terminal_tasks=1,
    )

    complete(persistent, "task-1")
    complete(persistent, "task-2")

    persistent.create("task-running")
    persistent.start("task-running")

    manager.run(apply=True)

    assert persistent.get("task-1") is None
    assert persistent.get("task-2") is not None
    assert persistent.get("task-running") is not None


def test_retention_survives_restart(tmp_path):
    manager, persistent, _ = make_manager(
        tmp_path,
        max_terminal_tasks=1,
    )

    complete(persistent, "task-1")
    complete(persistent, "task-2")

    manager.run(apply=True)

    restarted = PersistentTaskSupervisor(
        store=RuntimeStateStore(
            persistent.store.db_path
        ),
    )

    tasks = restarted.all_insertion_order()

    assert len(tasks) == 1
    assert tasks[0].task_id == "task-2"


def test_negative_limit_is_rejected(tmp_path):
    _, persistent, _ = make_manager(tmp_path)

    with pytest.raises(
        ValueError,
        match="max_terminal_tasks must be >= 0",
    ):
        TaskRetentionManager(
            persistent,
            max_terminal_tasks=-1,
        )


def test_retention_is_idempotent(tmp_path):
    manager, persistent, _ = make_manager(
        tmp_path,
        max_terminal_tasks=1,
    )

    complete(persistent, "task-1")
    complete(persistent, "task-2")

    first = manager.run(apply=True)
    second = manager.run(apply=True)

    assert first.pruned_terminal_tasks == 1
    assert second.pruned_terminal_tasks == 0

    assert len(persistent.all()) == 1
