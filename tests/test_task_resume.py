from core.persistent_task_supervisor import PersistentTaskSupervisor
from core.runtime_state import RuntimeStateStore
from core.task_queue import TaskQueue
from core.task_queue_coordinator import TaskQueueCoordinator
from core.task_resume import TaskResumeManager


def make_coordinator(path):
    store = RuntimeStateStore(path)
    return TaskQueueCoordinator(
        queue=TaskQueue(store),
        supervisor=PersistentTaskSupervisor(store=store),
    )


def test_running_task_is_safely_requeued_after_restart(tmp_path):
    path = tmp_path / "runtime.db"

    coordinator = make_coordinator(path)
    coordinator.submit("task-1", "build project")
    claimed = coordinator.claim_next()

    assert claimed is not None
    assert claimed.queued.status == "claimed"

    before = coordinator.get_supervised("task-1")
    assert before is not None
    assert before.status == "running"
    assert before.attempt == 1

    restarted = make_coordinator(path)
    results = TaskResumeManager(restarted).recover_unfinished()

    assert len(results) == 1
    assert results[0].action == "requeue"

    queued = restarted.get_queued("task-1")
    supervised = restarted.get_supervised("task-1")

    assert queued is not None
    assert queued.status == "queued"

    assert supervised is not None
    assert supervised.status == "retrying"
    assert supervised.attempt == 1


def test_recovered_task_resumes_without_duplicate_supervisor(tmp_path):
    path = tmp_path / "runtime.db"

    coordinator = make_coordinator(path)
    coordinator.submit("task-1", "build project")
    coordinator.claim_next()

    restarted = make_coordinator(path)
    TaskResumeManager(restarted).recover_unfinished()

    resumed = restarted.claim_next()

    assert resumed is not None
    assert resumed.queued.task_id == "task-1"
    assert resumed.queued.status == "claimed"

    supervised = restarted.get_supervised("task-1")

    assert supervised is not None
    assert supervised.status == "running"
    assert supervised.attempt == 2

    restarted.complete("task-1")

    final_queue = restarted.get_queued("task-1")
    final_supervised = restarted.get_supervised("task-1")

    assert final_queue is not None
    assert final_queue.status == "completed"

    assert final_supervised is not None
    assert final_supervised.status == "completed"


def test_retrying_task_is_requeued_without_extra_retry(tmp_path):
    path = tmp_path / "runtime.db"

    coordinator = make_coordinator(path)
    coordinator.submit("task-1", "build")
    coordinator.claim_next()

    coordinator.supervisor.retry(
        "task-1",
        reason="temporary failure",
    )

    restarted = make_coordinator(path)
    results = TaskResumeManager(restarted).recover_unfinished()

    assert len(results) == 1
    assert results[0].action == "requeue"

    supervised = restarted.get_supervised("task-1")
    queued = restarted.get_queued("task-1")

    assert supervised is not None
    assert supervised.status == "retrying"
    assert supervised.attempt == 1

    assert queued is not None
    assert queued.status == "queued"


def test_missing_supervisor_record_is_requeued(tmp_path):
    path = tmp_path / "runtime.db"

    store = RuntimeStateStore(path)
    queue = TaskQueue(store)
    queue.enqueue("task-1", "build")
    queue.claim_next()

    coordinator = TaskQueueCoordinator(
        queue=queue,
        supervisor=PersistentTaskSupervisor(store=store),
    )

    result = TaskResumeManager(coordinator).recover_unfinished()

    assert result[0].action == "requeue"

    queued = coordinator.get_queued("task-1")
    assert queued is not None
    assert queued.status == "queued"


def test_terminal_supervisor_state_is_reconciled(tmp_path):
    path = tmp_path / "runtime.db"

    coordinator = make_coordinator(path)
    coordinator.submit("task-1", "build")
    coordinator.claim_next()
    coordinator.complete("task-1")

    # Simulate a stale claimed queue entry.
    coordinator.queue._tasks = [
        coordinator.get_queued("task-1").__class__(
            task_id="task-1",
            payload="build",
            priority=0,
            status="claimed",
        )
    ]
    coordinator.queue._save()

    restarted = make_coordinator(path)
    results = TaskResumeManager(restarted).recover_unfinished()

    assert results[0].action == "reconcile"

    queued = restarted.get_queued("task-1")
    assert queued is not None
    assert queued.status == "completed"
