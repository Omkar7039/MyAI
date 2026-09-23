from core.runtime_state import RuntimeStateStore
from core.task_queue import TaskQueue


def test_enqueue_and_persist(tmp_path):
    path = tmp_path / "runtime.db"

    queue = TaskQueue(RuntimeStateStore(path))
    task = queue.enqueue("task-1", "do something")

    assert task.status == "queued"
    assert queue.get("task-1") == task

    restarted = TaskQueue(RuntimeStateStore(path))
    assert restarted.get("task-1") == task


def test_claim_uses_highest_priority(tmp_path):
    queue = TaskQueue(RuntimeStateStore(tmp_path / "runtime.db"))

    queue.enqueue("low", "low", priority=1)
    queue.enqueue("high", "high", priority=10)
    queue.enqueue("medium", "medium", priority=5)

    claimed = queue.claim_next()

    assert claimed is not None
    assert claimed.task_id == "high"
    assert claimed.status == "claimed"


def test_fifo_for_equal_priority(tmp_path):
    queue = TaskQueue(RuntimeStateStore(tmp_path / "runtime.db"))

    queue.enqueue("first", "first", priority=5)
    queue.enqueue("second", "second", priority=5)

    claimed = queue.claim_next()

    assert claimed is not None
    assert claimed.task_id == "first"


def test_complete_and_fail(tmp_path):
    queue = TaskQueue(RuntimeStateStore(tmp_path / "runtime.db"))

    queue.enqueue("ok", "success")
    queue.enqueue("bad", "failure")

    queue.claim_next()
    queue.claim_next()

    assert queue.complete("ok").status == "completed"
    assert queue.fail("bad").status == "failed"


def test_restart_preserves_claimed_state(tmp_path):
    path = tmp_path / "runtime.db"

    queue = TaskQueue(RuntimeStateStore(path))
    queue.enqueue("task-1", "work")

    claimed = queue.claim_next()
    assert claimed is not None

    restarted = TaskQueue(RuntimeStateStore(path))
    restored = restarted.get("task-1")

    assert restored is not None
    assert restored.status == "claimed"


def test_duplicate_task_rejected(tmp_path):
    queue = TaskQueue(RuntimeStateStore(tmp_path / "runtime.db"))

    queue.enqueue("task-1", "work")

    try:
        queue.enqueue("task-1", "again")
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate task was accepted")


def test_empty_queue_claim_returns_none(tmp_path):
    queue = TaskQueue(RuntimeStateStore(tmp_path / "runtime.db"))

    assert queue.claim_next() is None


def test_remove_and_clear(tmp_path):
    queue = TaskQueue(RuntimeStateStore(tmp_path / "runtime.db"))

    queue.enqueue("task-1", "one")
    queue.enqueue("task-2", "two")

    queue.remove("task-1")
    assert queue.get("task-1") is None
    assert queue.get("task-2") is not None

    queue.clear()
    assert queue.all() == ()
