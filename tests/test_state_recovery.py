from core.runtime_state import RuntimeStateStore
from core.state_recovery import RuntimeStateRecovery
from experience.persistent_learning_state import (
    PersistentLearningState,
)


def test_learning_state_corruption_is_quarantined_and_cleared(
    tmp_path,
):
    runtime = RuntimeStateStore(
        tmp_path / "runtime.db"
    )
    learning = PersistentLearningState(runtime)

    runtime.set(
        learning.KEY,
        '{"version":2,"changes":"broken","history":{}}',
    )

    recovery = RuntimeStateRecovery(
        runtime_store=runtime,
    )

    result = recovery.recover_learning_state(
        state=learning,
        error=RuntimeError("invalid state"),
    )

    assert result.recovered is True
    assert result.state_name == "learning"
    assert result.quarantined_key is not None
    assert result.quarantined_key.startswith(
        "recovery.quarantine.learning."
    )

    assert runtime.value(learning.KEY) is None
    assert runtime.value(result.quarantined_key) == (
        '{"version":2,"changes":"broken","history":{}}'
    )


def test_learning_state_recovery_does_not_change_other_state(
    tmp_path,
):
    runtime = RuntimeStateStore(
        tmp_path / "runtime.db"
    )
    learning = PersistentLearningState(runtime)

    runtime.set(
        learning.KEY,
        '{"version":2,"changes":"broken","history":{}}',
    )
    runtime.set(
        "runtime.status",
        "ready",
    )

    RuntimeStateRecovery(
        runtime_store=runtime,
    ).recover_learning_state(
        state=learning,
        error=RuntimeError("invalid state"),
    )

    assert runtime.value(
        "runtime.status"
    ) == "ready"


def test_missing_learning_state_is_not_treated_as_recovery(
    tmp_path,
):
    runtime = RuntimeStateStore(
        tmp_path / "runtime.db"
    )
    learning = PersistentLearningState(runtime)

    result = RuntimeStateRecovery(
        runtime_store=runtime,
    ).recover_learning_state(
        state=learning,
        error=RuntimeError("unused"),
    )

    assert result.recovered is False
    assert result.quarantined_key is None


def test_runtime_value_is_quarantined_and_cleared(
    tmp_path,
):
    runtime = RuntimeStateStore(
        tmp_path / "runtime.db"
    )

    runtime.set(
        "runtime.last_exit_code",
        "invalid",
    )

    recovery = RuntimeStateRecovery(
        runtime_store=runtime,
    )

    result = recovery.recover_runtime_value(
        key="runtime.last_exit_code",
        error=ValueError("invalid exit code"),
    )

    assert result.recovered is True
    assert result.state_name == (
        "runtime.last_exit_code"
    )
    assert result.quarantined_key is not None
    assert runtime.value(
        "runtime.last_exit_code"
    ) is None
    assert runtime.value(
        result.quarantined_key
    ) == "invalid"


def test_runtime_recovery_does_not_affect_other_values(
    tmp_path,
):
    runtime = RuntimeStateStore(
        tmp_path / "runtime.db"
    )

    runtime.set(
        "runtime.last_exit_code",
        "invalid",
    )
    runtime.set(
        "runtime.status",
        "ready",
    )

    RuntimeStateRecovery(
        runtime_store=runtime,
    ).recover_runtime_value(
        key="runtime.last_exit_code",
        error=ValueError("invalid"),
    )

    assert runtime.value(
        "runtime.status"
    ) == "ready"


def test_empty_runtime_key_is_rejected(tmp_path):
    runtime = RuntimeStateStore(
        tmp_path / "runtime.db"
    )

    try:
        RuntimeStateRecovery(
            runtime_store=runtime,
        ).recover_runtime_value(
            key=" ",
            error=ValueError("invalid"),
        )
    except ValueError as exc:
        assert str(exc) == "key must not be empty"
    else:
        raise AssertionError("expected ValueError")
