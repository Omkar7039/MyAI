from core.runtime_lifecycle import RuntimeLifecycle
from core.runtime_services import RuntimeServices
from core.runtime_state import RuntimeStateStore


def make_services(path):
    return RuntimeServices.create(
        RuntimeStateStore(path),
        max_task_terminal_entries=1,
    )


def test_production_queue_restart_resume_and_retention(tmp_path):
    path = tmp_path / "runtime.db"

    # First runtime: create work and leave it running.
    lifecycle = RuntimeLifecycle(path)
    lifecycle.startup()
    lifecycle.mark_ready()

    services = make_services(path)
    coordinator = services.task_queue_coordinator

    coordinator.submit(
        "task-1",
        "build project",
        priority=10,
    )
    coordinator.submit(
        "task-2",
        "run tests",
        priority=5,
    )

    first = coordinator.claim_next()

    assert first is not None
    assert first.queued.task_id == "task-1"

    supervised = coordinator.get_supervised("task-1")
    assert supervised is not None
    assert supervised.status == "running"

    # Simulate an unclean process termination.
    lifecycle.shutdown(exit_code=1)

    # Restart: recover unfinished work.
    restarted_lifecycle = RuntimeLifecycle(path)
    startup = restarted_lifecycle.startup()

    assert startup.previous_clean_shutdown is False

    restarted = make_services(path)

    report = restarted.recover_tasks_if_needed(
        previous_clean_shutdown=False,
    )

    assert report is not None
    assert report.total_unfinished == 1
    assert report.requeued == 1
    assert report.reconciled == 0
    assert report.failed == 0

    queued = restarted.get_queued("task-1")
    recovered_supervised = restarted.get_supervised("task-1")

    assert queued is not None
    assert queued.status == "queued"

    assert recovered_supervised is not None
    assert recovered_supervised.status == "retrying"
    assert recovered_supervised.attempt == 1

    # Resume the interrupted task.
    resumed = restarted.task_queue_coordinator.claim_next()

    assert resumed is not None
    assert resumed.queued.task_id == "task-1"

    resumed_supervised = restarted.get_supervised("task-1")

    assert resumed_supervised is not None
    assert resumed_supervised.status == "running"
    assert resumed_supervised.attempt == 2

    restarted.task_queue_coordinator.complete(
        "task-1",
        reason="completed after restart",
    )

    final_task = restarted.get_supervised("task-1")
    final_queue = restarted.get_queued("task-1")

    assert final_task is not None
    assert final_task.status == "completed"
    assert final_task.attempt == 2

    assert final_queue is not None
    assert final_queue.status == "completed"

    # Second task remains runnable.
    next_task = restarted.task_queue_coordinator.claim_next()

    assert next_task is not None
    assert next_task.queued.task_id == "task-2"

    restarted.task_queue_coordinator.complete(
        "task-2",
        reason="completed",
    )

    # Queue retention keeps only the newest terminal record.
    retention = restarted.apply_task_queue_retention()

    assert retention.existing_terminal_tasks == 2
    assert retention.retained_terminal_tasks == 1
    assert retention.pruned_terminal_tasks == 1
    assert retention.active_tasks == 0

    remaining = restarted.task_queue_coordinator.queue.all()

    assert len(remaining) == 1
    assert remaining[0].task_id == "task-2"

    # Resume report remains available for operational inspection.
    stored_report = restarted.resume_report()

    assert stored_report is not None
    assert stored_report.total_unfinished == 1
    assert stored_report.requeued == 1
