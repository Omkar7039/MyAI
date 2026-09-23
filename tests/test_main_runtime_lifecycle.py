from __future__ import annotations

from core.runtime_lifecycle import RuntimeLifecycle
from core.runtime_services import RuntimeServices
from core.runtime_state import RuntimeStateStore


def test_main_runtime_lifecycle_startup_recovery_ready_shutdown(
    tmp_path,
):
    store = RuntimeStateStore(
        tmp_path / "runtime.db"
    )

    lifecycle = RuntimeLifecycle(store)
    services = RuntimeServices.create(store)

    # Startup
    startup = lifecycle.startup()

    assert startup.current_status == "starting"
    assert startup.previous_clean_shutdown is False

    # Recovery must happen before readiness.
    recovery = services.recover_learning_state_if_needed()
    assert recovery is None

    task_resume = services.recover_tasks_if_needed(
        previous_clean_shutdown=startup.previous_clean_shutdown,
    )
    assert task_resume is None

    # Runtime must pass readiness before becoming ready.
    readiness = services.check_readiness()

    assert readiness.ready is True

    assert lifecycle.mark_ready() == "ready"
    assert store.value("runtime.status") == "ready"

    # Clean shutdown.
    shutdown = lifecycle.shutdown(exit_code=0)

    assert shutdown.clean is True
    assert shutdown.current_status == "stopped"
    assert store.value("runtime.status") == "stopped"
    assert store.value("runtime.clean_shutdown") == "true"
    assert store.value("runtime.last_exit_code") == "0"


def test_main_runtime_lifecycle_restart_detects_previous_clean_shutdown(
    tmp_path,
):
    db_path = tmp_path / "runtime.db"

    # First process.
    first_store = RuntimeStateStore(db_path)
    first_lifecycle = RuntimeLifecycle(first_store)

    first_lifecycle.startup()
    first_lifecycle.mark_ready()
    first_lifecycle.shutdown(exit_code=0)

    # Second process.
    second_store = RuntimeStateStore(db_path)
    second_lifecycle = RuntimeLifecycle(second_store)

    startup = second_lifecycle.startup()

    assert startup.previous_clean_shutdown is True
    assert startup.previous_status == "stopped"
    assert startup.current_status == "starting"

    assert second_lifecycle.mark_ready() == "ready"

    second_lifecycle.shutdown(exit_code=0)


def test_main_runtime_lifecycle_unclean_shutdown_is_detected(
    tmp_path,
):
    db_path = tmp_path / "runtime.db"

    # Simulate process that stops abnormally.
    first_store = RuntimeStateStore(db_path)
    first_lifecycle = RuntimeLifecycle(first_store)

    first_lifecycle.startup()
    first_lifecycle.mark_ready()
    first_lifecycle.shutdown(exit_code=130)

    # Next process must detect the unclean shutdown.
    second_store = RuntimeStateStore(db_path)
    second_lifecycle = RuntimeLifecycle(second_store)

    startup = second_lifecycle.startup()

    assert startup.previous_clean_shutdown is False
    assert startup.previous_status == "stopped_unclean"
    assert startup.current_status == "starting"

    assert second_lifecycle.mark_ready() == "ready"

    second_lifecycle.shutdown(exit_code=0)
