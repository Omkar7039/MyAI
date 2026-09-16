from core.runtime_lifecycle import (
    RuntimeLifecycle,
)
from core.runtime_state import RuntimeStateStore


def make_lifecycle(tmp_path):
    store = RuntimeStateStore(
        tmp_path / "runtime.db"
    )
    return RuntimeLifecycle(store), store


def test_first_start_detects_no_previous_clean_shutdown(tmp_path):
    lifecycle, store = make_lifecycle(tmp_path)

    result = lifecycle.startup()

    assert result.previous_clean_shutdown is False
    assert result.previous_status is None
    assert result.current_status == "starting"
    assert store.value("runtime.status") == "starting"
    assert store.value("runtime.clean_shutdown") == "false"


def test_start_after_clean_shutdown_recovers_clean_state(tmp_path):
    lifecycle, store = make_lifecycle(tmp_path)

    store.set(
        "runtime.status",
        "stopped",
    )
    store.set(
        "runtime.clean_shutdown",
        "true",
    )

    result = lifecycle.startup()

    assert result.previous_clean_shutdown is True
    assert result.previous_status == "stopped"
    assert store.value("runtime.status") == "starting"
    assert store.value("runtime.clean_shutdown") == "false"


def test_start_after_unclean_shutdown_detects_unclean_state(tmp_path):
    lifecycle, store = make_lifecycle(tmp_path)

    store.set(
        "runtime.status",
        "stopped_unclean",
    )
    store.set(
        "runtime.clean_shutdown",
        "false",
    )

    result = lifecycle.startup()

    assert result.previous_clean_shutdown is False
    assert result.previous_status == "stopped_unclean"
    assert store.value("runtime.status") == "starting"


def test_mark_ready_updates_status(tmp_path):
    lifecycle, store = make_lifecycle(tmp_path)

    lifecycle.startup()

    assert lifecycle.mark_ready() == "ready"
    assert store.value("runtime.status") == "ready"


def test_successful_shutdown_marks_clean(tmp_path):
    lifecycle, store = make_lifecycle(tmp_path)

    lifecycle.startup()
    lifecycle.mark_ready()

    result = lifecycle.shutdown(
        exit_code=0,
    )

    assert result.clean is True
    assert result.previous_status == "ready"
    assert result.current_status == "stopped"
    assert store.value("runtime.status") == "stopped"
    assert store.value("runtime.clean_shutdown") == "true"
    assert store.value("runtime.last_exit_code") == "0"


def test_nonzero_shutdown_marks_unclean(tmp_path):
    lifecycle, store = make_lifecycle(tmp_path)

    lifecycle.startup()
    lifecycle.mark_ready()

    result = lifecycle.shutdown(
        exit_code=130,
    )

    assert result.clean is False
    assert result.previous_status == "ready"
    assert result.current_status == "stopped_unclean"
    assert store.value("runtime.status") == "stopped_unclean"
    assert store.value("runtime.clean_shutdown") == "false"
    assert store.value("runtime.last_exit_code") == "130"


def test_shutdown_is_persisted_across_new_lifecycle_instance(
    tmp_path,
):
    db = tmp_path / "runtime.db"

    first = RuntimeLifecycle(
        RuntimeStateStore(db)
    )

    first.startup()
    first.mark_ready()
    first.shutdown(exit_code=0)

    second = RuntimeLifecycle(
        RuntimeStateStore(db)
    )

    startup = second.startup()

    assert startup.previous_clean_shutdown is True
    assert startup.previous_status == "stopped"
