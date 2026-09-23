from core.runtime_services import RuntimeServices
from core.task_queue import TaskQueue


def test_unclean_start_recovers_unfinished_task(tmp_path):
    path = tmp_path / "runtime.db"

    from core.runtime_state import RuntimeStateStore
    services = RuntimeServices.create(RuntimeStateStore(path))

    coordinator = services.task_queue_coordinator
    assert coordinator is not None

    coordinator.submit("task-1", "build project")
    claimed = coordinator.claim_next()

    assert claimed is not None

    report = services.recover_tasks_if_needed(
        previous_clean_shutdown=False,
    )

    assert report is not None
    assert report.total_unfinished == 1
    assert report.requeued == 1
    assert report.reconciled == 0
    assert report.failed == 0

    queued = coordinator.get_queued("task-1")
    supervised = coordinator.get_supervised("task-1")

    assert queued is not None
    assert queued.status == "queued"

    assert supervised is not None
    assert supervised.status == "retrying"


def test_clean_start_does_not_recover_tasks(tmp_path):
    from core.runtime_state import RuntimeStateStore

    services = RuntimeServices.create(
        RuntimeStateStore(tmp_path / "runtime.db")
    )

    coordinator = services.task_queue_coordinator
    assert coordinator is not None

    coordinator.submit("task-1", "build")
    coordinator.claim_next()

    report = services.recover_tasks_if_needed(
        previous_clean_shutdown=True,
    )

    assert report is None

    queued = coordinator.get_queued("task-1")
    assert queued is not None
    assert queued.status == "claimed"


def test_resume_report_is_visible_in_status_snapshot(tmp_path):
    from core.runtime_state import RuntimeStateStore

    services = RuntimeServices.create(
        RuntimeStateStore(tmp_path / "runtime.db")
    )

    coordinator = services.task_queue_coordinator
    assert coordinator is not None

    coordinator.submit("task-1", "build")
    coordinator.claim_next()

    report = services.recover_tasks_if_needed(
        previous_clean_shutdown=False,
    )

    assert report is not None

    snapshot = services.status_snapshot()

    assert snapshot.resume_total_unfinished == 1
    assert snapshot.resume_requeued == 1
    assert snapshot.resume_reconciled == 0
    assert snapshot.resume_failed == 0


def test_resume_report_survives_service_restart(tmp_path):
    from core.runtime_state import RuntimeStateStore

    path = tmp_path / "runtime.db"

    services = RuntimeServices.create(
        RuntimeStateStore(path)
    )

    coordinator = services.task_queue_coordinator
    assert coordinator is not None

    coordinator.submit("task-1", "build")
    coordinator.claim_next()

    services.recover_tasks_if_needed(
        previous_clean_shutdown=False,
    )

    restarted = RuntimeServices.create(
        RuntimeStateStore(path)
    )

    snapshot = restarted.status_snapshot()

    assert snapshot.resume_total_unfinished == 1
    assert snapshot.resume_requeued == 1


def test_reconciled_terminal_task_is_reported(tmp_path):
    from core.runtime_state import RuntimeStateStore

    services = RuntimeServices.create(
        RuntimeStateStore(tmp_path / "runtime.db")
    )

    coordinator = services.task_queue_coordinator
    assert coordinator is not None

    coordinator.submit("task-1", "build")
    coordinator.claim_next()
    coordinator.complete("task-1")

    # Simulate stale claimed queue state.
    original = coordinator.get_queued("task-1")
    assert original is not None

    coordinator.queue._tasks = [
        original.__class__(
            task_id=original.task_id,
            payload=original.payload,
            priority=original.priority,
            status="claimed",
        )
    ]
    coordinator.queue._save()

    report = services.recover_tasks_if_needed(
        previous_clean_shutdown=False,
    )

    assert report is not None
    assert report.reconciled == 1
    assert report.failed == 0
