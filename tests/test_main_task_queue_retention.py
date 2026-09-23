from core.runtime_services import RuntimeServices
from core.runtime_state import RuntimeStateStore
from main import handle_runtime_command


def make_services(tmp_path):
    return RuntimeServices.create(
        RuntimeStateStore(tmp_path / "runtime.db"),
        max_task_terminal_entries=1,
    )


def complete_task(services, task_id):
    coordinator = services.task_queue_coordinator
    coordinator.submit(task_id, task_id)
    claimed = coordinator.claim_next()
    assert claimed is not None
    coordinator.complete(task_id)


def test_task_retention_preview_command(tmp_path, capsys):
    services = make_services(tmp_path)

    complete_task(services, "task-1")
    complete_task(services, "task-2")

    handled = handle_runtime_command(
        "/task-retention",
        services,
    )

    assert handled is True

    output = capsys.readouterr().out

    assert "Task queue retention preview:" in output
    assert "Terminal tasks: 2" in output
    assert "Terminal tasks retained: 1" in output
    assert "Terminal tasks to prune: 1" in output


def test_task_retention_apply_command(tmp_path, capsys):
    services = make_services(tmp_path)

    complete_task(services, "task-1")
    complete_task(services, "task-2")

    handled = handle_runtime_command(
        "/task-retention apply",
        services,
    )

    assert handled is True

    output = capsys.readouterr().out

    assert "Task queue retention applied:" in output
    assert "Terminal tasks pruned: 1" in output

    remaining = services.task_queue_coordinator.queue.all()

    assert len(remaining) == 1
    assert remaining[0].task_id == "task-2"


def test_task_retention_preview_is_non_mutating(tmp_path):
    services = make_services(tmp_path)

    complete_task(services, "task-1")
    complete_task(services, "task-2")

    before = services.task_queue_coordinator.queue.all()

    handled = handle_runtime_command(
        "/task-retention",
        services,
    )

    after = services.task_queue_coordinator.queue.all()

    assert handled is True
    assert after == before


def test_unknown_command_remains_unhandled(tmp_path):
    services = make_services(tmp_path)

    assert (
        handle_runtime_command(
            "/task-retention-unknown",
            services,
        )
        is False
    )
