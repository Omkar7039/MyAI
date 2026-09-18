from core.runtime_consistency import (
    RuntimeConsistencyChecker,
    RuntimeConsistencyReport,
)
from core.runtime_lifecycle import RuntimeLifecycle
from core.runtime_state import RuntimeStateStore


def make_store(tmp_path):
    return RuntimeStateStore(
        tmp_path / "runtime.db"
    )


def test_empty_runtime_state_is_consistent(tmp_path):
    store = make_store(tmp_path)

    result = RuntimeConsistencyChecker(store).check()

    assert isinstance(result, RuntimeConsistencyReport)
    assert result.consistent is True
    assert result.issues == ()


def test_ready_runtime_is_consistent(tmp_path):
    store = make_store(tmp_path)

    lifecycle = RuntimeLifecycle(store)
    lifecycle.startup()
    lifecycle.mark_ready()

    result = RuntimeConsistencyChecker(store).check()

    assert result.consistent is True
    assert result.issues == ()


def test_clean_stopped_runtime_is_consistent(tmp_path):
    store = make_store(tmp_path)

    lifecycle = RuntimeLifecycle(store)
    lifecycle.startup()
    lifecycle.mark_ready()
    lifecycle.shutdown(exit_code=0)

    result = RuntimeConsistencyChecker(store).check()

    assert result.consistent is True
    assert result.issues == ()


def test_unclean_stopped_runtime_is_consistent(tmp_path):
    store = make_store(tmp_path)

    lifecycle = RuntimeLifecycle(store)
    lifecycle.startup()
    lifecycle.mark_ready()
    lifecycle.shutdown(exit_code=130)

    result = RuntimeConsistencyChecker(store).check()

    assert result.consistent is True
    assert result.issues == ()


def test_invalid_status_is_detected(tmp_path):
    store = make_store(tmp_path)

    store.set(
        RuntimeLifecycle.STATUS_KEY,
        "broken",
    )

    result = RuntimeConsistencyChecker(store).check()

    assert result.consistent is False
    assert "invalid runtime status: broken" in result.issues


def test_clean_shutdown_true_on_active_runtime_is_detected(
    tmp_path,
):
    store = make_store(tmp_path)

    store.set(
        RuntimeLifecycle.STATUS_KEY,
        "ready",
    )
    store.set(
        RuntimeLifecycle.CLEAN_SHUTDOWN_KEY,
        "true",
    )

    result = RuntimeConsistencyChecker(store).check()

    assert result.consistent is False
    assert any(
        "clean_shutdown=true" in issue
        for issue in result.issues
    )


def test_stopped_runtime_requires_clean_shutdown(tmp_path):
    store = make_store(tmp_path)

    store.set(
        RuntimeLifecycle.STATUS_KEY,
        "stopped",
    )
    store.set(
        RuntimeLifecycle.CLEAN_SHUTDOWN_KEY,
        "false",
    )

    result = RuntimeConsistencyChecker(store).check()

    assert result.consistent is False
    assert any(
        "must have clean_shutdown=true" in issue
        for issue in result.issues
    )


def test_stopped_runtime_rejects_nonzero_exit_code(tmp_path):
    store = make_store(tmp_path)

    store.set(
        RuntimeLifecycle.STATUS_KEY,
        "stopped",
    )
    store.set(
        RuntimeLifecycle.CLEAN_SHUTDOWN_KEY,
        "true",
    )
    store.set(
        RuntimeLifecycle.LAST_EXIT_CODE_KEY,
        "130",
    )

    result = RuntimeConsistencyChecker(store).check()

    assert result.consistent is False
    assert any(
        "exit code 0" in issue
        for issue in result.issues
    )


def test_unclean_runtime_rejects_zero_exit_code(tmp_path):
    store = make_store(tmp_path)

    store.set(
        RuntimeLifecycle.STATUS_KEY,
        "stopped_unclean",
    )
    store.set(
        RuntimeLifecycle.CLEAN_SHUTDOWN_KEY,
        "false",
    )
    store.set(
        RuntimeLifecycle.LAST_EXIT_CODE_KEY,
        "0",
    )

    result = RuntimeConsistencyChecker(store).check()

    assert result.consistent is False
    assert any(
        "must not have exit code 0" in issue
        for issue in result.issues
    )


def test_invalid_clean_shutdown_value_is_detected(tmp_path):
    store = make_store(tmp_path)

    store.set(
        RuntimeLifecycle.STATUS_KEY,
        "ready",
    )
    store.set(
        RuntimeLifecycle.CLEAN_SHUTDOWN_KEY,
        "maybe",
    )

    result = RuntimeConsistencyChecker(store).check()

    assert result.consistent is False
    assert "invalid persisted clean-shutdown value" in result.issues


def test_invalid_exit_code_is_detected(tmp_path):
    store = make_store(tmp_path)

    store.set(
        RuntimeLifecycle.STATUS_KEY,
        "ready",
    )
    store.set(
        RuntimeLifecycle.LAST_EXIT_CODE_KEY,
        "invalid",
    )

    result = RuntimeConsistencyChecker(store).check()

    assert result.consistent is False
    assert "invalid persisted runtime exit code" in result.issues


def test_metadata_without_status_is_detected(tmp_path):
    store = make_store(tmp_path)

    store.set(
        RuntimeLifecycle.CLEAN_SHUTDOWN_KEY,
        "false",
    )

    result = RuntimeConsistencyChecker(store).check()

    assert result.consistent is False
    assert any(
        "without a runtime status" in issue
        for issue in result.issues
    )


def test_consistency_check_is_read_only(tmp_path):
    store = make_store(tmp_path)

    lifecycle = RuntimeLifecycle(store)
    lifecycle.startup()
    lifecycle.mark_ready()

    before = store.all()

    RuntimeConsistencyChecker(store).check()

    after = store.all()

    assert before == after
