from core.runtime_services import RuntimeServices
from core.runtime_state import RuntimeStateStore


def make_services(tmp_path, limit=1):
    return RuntimeServices.create(
        RuntimeStateStore(tmp_path / "runtime.db"),
        max_task_terminal_entries=limit,
    )


def complete_task(services, task_id):
    coordinator = services.task_queue_coordinator
    coordinator.submit(task_id, task_id)
    claimed = coordinator.claim_next()
    assert claimed is not None
    coordinator.complete(task_id)


def test_runtime_services_previews_queue_retention(tmp_path):
    services = make_services(tmp_path, limit=1)

    complete_task(services, "task-1")
    complete_task(services, "task-2")

    report = services.preview_task_queue_retention()

    assert report.existing_terminal_tasks == 2
    assert report.retained_terminal_tasks == 1
    assert report.pruned_terminal_tasks == 1
    assert report.applied is False

    assert len(services.task_queue_coordinator.queue.all()) == 2


def test_runtime_services_applies_queue_retention(tmp_path):
    services = make_services(tmp_path, limit=1)

    complete_task(services, "task-1")
    complete_task(services, "task-2")

    report = services.apply_task_queue_retention()

    assert report.existing_terminal_tasks == 2
    assert report.retained_terminal_tasks == 1
    assert report.pruned_terminal_tasks == 1
    assert report.applied is True

    remaining = services.task_queue_coordinator.queue.all()

    assert len(remaining) == 1
    assert remaining[0].task_id == "task-2"


def test_runtime_services_retention_keeps_active_tasks(tmp_path):
    services = make_services(tmp_path, limit=0)
    coordinator = services.task_queue_coordinator

    coordinator.submit("claimed", "claimed")
    claimed = coordinator.claim_next()
    assert claimed is not None
    assert claimed.queued.task_id == "claimed"

    coordinator.submit("terminal", "terminal")
    terminal = coordinator.claim_next()
    assert terminal is not None
    assert terminal.queued.task_id == "terminal"
    coordinator.complete("terminal")

    coordinator.submit("queued", "queued")

    report = services.apply_task_queue_retention()

    assert report.pruned_terminal_tasks == 1
    assert report.active_tasks == 2

    queued = coordinator.get_queued("queued")
    claimed = coordinator.get_queued("claimed")

    assert queued is not None
    assert queued.status == "queued"

    assert claimed is not None
    assert claimed.status == "claimed"


def test_runtime_services_rejects_negative_queue_retention_limit(tmp_path):
    try:
        RuntimeServices.create(
            RuntimeStateStore(tmp_path / "runtime.db"),
            max_task_terminal_entries=-1,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "negative queue retention limit was accepted"
        )


def test_queue_retention_configuration_is_per_service(tmp_path):
    services_one = RuntimeServices.create(
        RuntimeStateStore(tmp_path / "one.db"),
        max_task_terminal_entries=3,
    )
    services_two = RuntimeServices.create(
        RuntimeStateStore(tmp_path / "two.db"),
        max_task_terminal_entries=7,
    )

    assert services_one.task_queue_retention.max_terminal_tasks == 3
    assert services_two.task_queue_retention.max_terminal_tasks == 7
