from core.runtime_state import RuntimeStateStore
from core.task_queue import TaskQueue
from core.task_queue_retention import TaskQueueRetentionManager


def make_queue(path):
    return TaskQueue(RuntimeStateStore(path))


def complete_task(queue, task_id):
    queue.enqueue(task_id, task_id)
    queue.claim_next()
    queue.complete(task_id)


def fail_task(queue, task_id):
    queue.enqueue(task_id, task_id)
    queue.claim_next()
    queue.fail(task_id)


def test_preview_does_not_modify_queue(tmp_path):
    queue = make_queue(tmp_path / "runtime.db")

    complete_task(queue, "task-1")
    complete_task(queue, "task-2")
    queue.enqueue("active", "active")

    manager = TaskQueueRetentionManager(
        queue,
        max_terminal_tasks=1,
    )

    result = manager.run(apply=False)

    assert result.existing_terminal_tasks == 2
    assert result.retained_terminal_tasks == 1
    assert result.pruned_terminal_tasks == 1
    assert result.active_tasks == 1
    assert result.applied is False

    assert len(queue.all()) == 3


def test_apply_prunes_oldest_terminal_tasks(tmp_path):
    queue = make_queue(tmp_path / "runtime.db")

    complete_task(queue, "old-1")
    complete_task(queue, "old-2")
    complete_task(queue, "keep")

    manager = TaskQueueRetentionManager(
        queue,
        max_terminal_tasks=1,
    )

    result = manager.run(apply=True)

    assert result.pruned_terminal_tasks == 2
    assert result.applied is True

    remaining = queue.all()

    assert len(remaining) == 1
    assert remaining[0].task_id == "keep"


def test_active_tasks_are_never_pruned(tmp_path):
    queue = make_queue(tmp_path / "runtime.db")

    queue.enqueue("claimed", "claimed")
    claimed = queue.claim_next()
    assert claimed is not None
    assert claimed.task_id == "claimed"

    complete_task(queue, "terminal-1")
    complete_task(queue, "terminal-2")

    queue.enqueue("queued", "queued")

    manager = TaskQueueRetentionManager(
        queue,
        max_terminal_tasks=0,
    )

    result = manager.run(apply=True)

    assert result.existing_terminal_tasks == 2
    assert result.pruned_terminal_tasks == 2
    assert result.active_tasks == 2

    assert queue.get("queued") is not None
    assert queue.get("queued").status == "queued"

    assert queue.get("claimed") is not None
    assert queue.get("claimed").status == "claimed"


def test_failed_tasks_are_retained_and_pruned(tmp_path):
    queue = make_queue(tmp_path / "runtime.db")

    fail_task(queue, "failed-1")
    fail_task(queue, "failed-2")

    manager = TaskQueueRetentionManager(
        queue,
        max_terminal_tasks=1,
    )

    result = manager.run(apply=True)

    assert result.existing_terminal_tasks == 2
    assert result.pruned_terminal_tasks == 1

    remaining = queue.all()
    assert len(remaining) == 1
    assert remaining[0].status == "failed"


def test_zero_retention_removes_all_terminal_tasks(tmp_path):
    queue = make_queue(tmp_path / "runtime.db")

    complete_task(queue, "task-1")
    fail_task(queue, "task-2")
    queue.enqueue("active", "active")

    manager = TaskQueueRetentionManager(
        queue,
        max_terminal_tasks=0,
    )

    result = manager.run(apply=True)

    assert result.existing_terminal_tasks == 2
    assert result.retained_terminal_tasks == 0
    assert result.pruned_terminal_tasks == 2

    remaining = queue.all()

    assert len(remaining) == 1
    assert remaining[0].task_id == "active"


def test_retention_is_idempotent(tmp_path):
    queue = make_queue(tmp_path / "runtime.db")

    complete_task(queue, "task-1")
    complete_task(queue, "task-2")

    manager = TaskQueueRetentionManager(
        queue,
        max_terminal_tasks=1,
    )

    first = manager.run(apply=True)
    second = manager.run(apply=True)

    assert first.pruned_terminal_tasks == 1
    assert second.pruned_terminal_tasks == 0
    assert len(queue.all()) == 1


def test_all_terminal_tasks_retained_when_under_limit(tmp_path):
    queue = make_queue(tmp_path / "runtime.db")

    complete_task(queue, "task-1")
    fail_task(queue, "task-2")

    manager = TaskQueueRetentionManager(
        queue,
        max_terminal_tasks=10,
    )

    result = manager.run(apply=True)

    assert result.existing_terminal_tasks == 2
    assert result.retained_terminal_tasks == 2
    assert result.pruned_terminal_tasks == 0
    assert len(queue.all()) == 2


def test_negative_limit_rejected(tmp_path):
    queue = make_queue(tmp_path / "runtime.db")

    try:
        TaskQueueRetentionManager(
            queue,
            max_terminal_tasks=-1,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("negative retention limit was accepted")


def test_retention_survives_restart(tmp_path):
    path = tmp_path / "runtime.db"

    queue = make_queue(path)

    complete_task(queue, "old")
    complete_task(queue, "keep")
    queue.enqueue("active", "active")

    manager = TaskQueueRetentionManager(
        queue,
        max_terminal_tasks=1,
    )
    manager.run(apply=True)

    restarted = make_queue(path)

    remaining = restarted.all()

    assert [task.task_id for task in remaining] == [
        "keep",
        "active",
    ]
