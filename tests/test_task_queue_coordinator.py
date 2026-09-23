from core.persistent_task_supervisor import PersistentTaskSupervisor
from core.runtime_state import RuntimeStateStore
from core.task_queue import TaskQueue
from core.task_queue_coordinator import TaskQueueCoordinator


def make_coordinator(path):
    store = RuntimeStateStore(path)
    return TaskQueueCoordinator(
        queue=TaskQueue(store),
        supervisor=PersistentTaskSupervisor(store=store),
    )


def test_submit_creates_durable_queue_entry(tmp_path):
    coordinator = make_coordinator(tmp_path / "runtime.db")

    task = coordinator.submit(
        "task-1",
        "build project",
        priority=5,
    )

    assert task.task_id == "task-1"
    assert task.status == "queued"

    restarted = make_coordinator(tmp_path / "runtime.db")
    restored = restarted.get_queued("task-1")

    assert restored == task


def test_claim_connects_queue_and_supervisor(tmp_path):
    coordinator = make_coordinator(tmp_path / "runtime.db")

    coordinator.submit("task-1", "build")

    claimed = coordinator.claim_next()

    assert claimed is not None
    assert claimed.queued.task_id == "task-1"
    assert claimed.queued.status == "claimed"

    supervised = coordinator.get_supervised("task-1")

    assert supervised is not None
    assert supervised.task_id == "task-1"
    assert supervised.status == "running"


def test_complete_updates_both_layers(tmp_path):
    coordinator = make_coordinator(tmp_path / "runtime.db")

    coordinator.submit("task-1", "build")
    coordinator.claim_next()
    coordinator.complete("task-1", reason="finished successfully")

    queued = coordinator.get_queued("task-1")
    supervised = coordinator.get_supervised("task-1")

    assert queued is not None
    assert queued.status == "completed"

    assert supervised is not None
    assert supervised.status == "completed"
    assert supervised.success is True
    assert supervised.reason == "finished successfully"


def test_fail_updates_both_layers(tmp_path):
    coordinator = make_coordinator(tmp_path / "runtime.db")

    coordinator.submit("task-1", "build")
    coordinator.claim_next()
    coordinator.fail("task-1", reason="build failed")

    queued = coordinator.get_queued("task-1")
    supervised = coordinator.get_supervised("task-1")

    assert queued is not None
    assert queued.status == "failed"

    assert supervised is not None
    assert supervised.status == "failed"
    assert supervised.success is False
    assert supervised.reason == "build failed"


def test_restart_preserves_queue_and_supervisor_state(tmp_path):
    path = tmp_path / "runtime.db"

    coordinator = make_coordinator(path)
    coordinator.submit("task-1", "build", priority=10)
    coordinator.claim_next()

    restarted = make_coordinator(path)

    queued = restarted.get_queued("task-1")
    supervised = restarted.get_supervised("task-1")

    assert queued is not None
    assert queued.status == "claimed"

    assert supervised is not None
    assert supervised.status == "running"


def test_multiple_tasks_claim_in_priority_order(tmp_path):
    coordinator = make_coordinator(tmp_path / "runtime.db")

    coordinator.submit("low", "low", priority=1)
    coordinator.submit("high", "high", priority=10)
    coordinator.submit("medium", "medium", priority=5)

    first = coordinator.claim_next()
    second = coordinator.claim_next()
    third = coordinator.claim_next()

    assert first is not None
    assert second is not None
    assert third is not None

    assert first.queued.task_id == "high"
    assert second.queued.task_id == "medium"
    assert third.queued.task_id == "low"


def test_duplicate_submit_rejected(tmp_path):
    coordinator = make_coordinator(tmp_path / "runtime.db")

    coordinator.submit("task-1", "first")

    try:
        coordinator.submit("task-1", "second")
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate task was accepted")


def test_empty_queue_returns_none(tmp_path):
    coordinator = make_coordinator(tmp_path / "runtime.db")

    assert coordinator.claim_next() is None
