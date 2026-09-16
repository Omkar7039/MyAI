from __future__ import annotations

import json

from core.runtime_diagnostics import RuntimeDiagnosticsChecker
from core.runtime_lifecycle import RuntimeLifecycle
from core.runtime_state import RuntimeStateStore
from experience.learning_state import LearningAppliedChange
from experience.learning_state_retention import LearningStateRetentionManager
from experience.persistent_learning_state import PersistentLearningState


def make_change(
    strategy: str,
    previous_score: float | None,
    applied_score: float,
) -> LearningAppliedChange:
    return LearningAppliedChange(
        strategy=strategy,
        previous_score=previous_score,
        applied_score=applied_score,
        observations=10,
        confidence=75.0,
    )


def test_production_runtime_restart_learning_retention_and_recovery(tmp_path):
    db_path = tmp_path / "runtime_state.db"

    # ------------------------------------------------------------
    # 1. First process startup
    # ------------------------------------------------------------
    store = RuntimeStateStore(db_path)
    lifecycle = RuntimeLifecycle(store)

    startup = lifecycle.startup()

    assert startup.current_status == "starting"
    assert startup.previous_clean_shutdown is False
    assert startup.previous_status is None

    assert lifecycle.mark_ready() == "ready"

    # ------------------------------------------------------------
    # 2. Persist governed learning state + rollback history
    # ------------------------------------------------------------
    learning = PersistentLearningState(store)

    property_1 = make_change("property", None, 80.0)
    property_2 = make_change("property", 80.0, 90.0)
    property_3 = make_change("property", 90.0, 95.0)

    learning.save(
        (property_3,),
        {
            "property": [
                property_1,
                property_2,
                property_3,
            ]
        },
    )

    loaded_changes, loaded_history = learning.load_with_history()

    assert len(loaded_changes) == 1
    assert loaded_changes[0].strategy == "property"
    assert len(loaded_history["property"]) == 3

    # ------------------------------------------------------------
    # 3. Apply retention
    # ------------------------------------------------------------
    retention = LearningStateRetentionManager(
        learning,
        max_rollback_entries=2,
    ).run(apply=True)

    assert retention.applied is True
    assert retention.scanned_strategies == 1
    assert retention.pruned_entries == 1
    assert retention.retained_entries == 2

    _, retained_history = learning.load_with_history()

    assert len(retained_history["property"]) == 2
    assert retained_history["property"][-1].applied_score == 95.0

    # ------------------------------------------------------------
    # 4. Clean shutdown
    # ------------------------------------------------------------
    shutdown = lifecycle.shutdown(exit_code=0)

    assert shutdown.clean is True
    assert shutdown.current_status == "stopped"

    # ------------------------------------------------------------
    # 5. Simulate a real process restart using a new store/object
    # ------------------------------------------------------------
    restarted_store = RuntimeStateStore(db_path)
    restarted_lifecycle = RuntimeLifecycle(restarted_store)

    restarted_startup = restarted_lifecycle.startup()

    assert restarted_startup.previous_clean_shutdown is True
    assert restarted_startup.previous_status == "stopped"
    assert restarted_startup.current_status == "starting"

    assert restarted_lifecycle.mark_ready() == "ready"

    restarted_learning = PersistentLearningState(restarted_store)

    restarted_changes, restarted_history = (
        restarted_learning.load_with_history()
    )

    assert len(restarted_changes) == 1
    assert restarted_changes[0].strategy == "property"
    assert len(restarted_history["property"]) == 2

    # ------------------------------------------------------------
    # 6. Runtime diagnostics after restart
    # ------------------------------------------------------------
    diagnostics = RuntimeDiagnosticsChecker(
        runtime_store=restarted_store,
        learning_state=restarted_learning,
    )

    health = diagnostics.check()

    assert health.runtime_status == "ready"
    assert health.clean_shutdown is False
    assert health.last_exit_code is None
    assert health.active_strategy_count == 1
    assert health.active_strategies == ("property",)
    assert health.rollback_available == ("property",)
    assert health.runtime_state_available is True
    assert health.learning_state_available is True
    assert health.healthy is True
    assert health.issues == ()

    # ------------------------------------------------------------
    # 7. Simulate corrupted learning state
    # ------------------------------------------------------------
    learning_key = "learning.governed.strategies"

    restarted_store.set(
        learning_key,
        "{ definitely-not-valid-json",
    )

    corrupted_learning = PersistentLearningState(restarted_store)

    recovery_checker = RuntimeDiagnosticsChecker(
        runtime_store=restarted_store,
        learning_state=corrupted_learning,
    )

    recovery = recovery_checker.recover_learning_state(
        ValueError("corrupted learning state"),
    )

    assert recovery.recovered is True
    assert recovery.state_name == "learning"
    assert recovery.quarantined_key.startswith(
        "recovery.quarantine.learning."
    )

    # ------------------------------------------------------------
    # 8. Recovery leaves the active learning state safely empty
    # ------------------------------------------------------------
    recovered_learning = PersistentLearningState(restarted_store)

    recovered_changes, recovered_history = (
        recovered_learning.load_with_history()
    )

    assert recovered_changes == ()
    assert recovered_history == {}

    # ------------------------------------------------------------
    # 9. Diagnostics can inspect the recovered state
    # ------------------------------------------------------------
    recovered_health = RuntimeDiagnosticsChecker(
        runtime_store=restarted_store,
        learning_state=recovered_learning,
    ).check()

    assert recovered_health.runtime_state_available is True
    assert recovered_health.learning_state_available is True
    assert recovered_health.active_strategy_count == 0
    assert recovered_health.active_strategies == ()
    assert recovered_health.healthy is True

    # Confirm the quarantine record is actually persisted.
    quarantine_value = restarted_store.value(
        recovery.quarantined_key
    )

    assert quarantine_value == "{ definitely-not-valid-json"


def test_runtime_unclean_shutdown_is_detected_after_restart(tmp_path):
    db_path = tmp_path / "runtime_state.db"

    first_store = RuntimeStateStore(db_path)
    first = RuntimeLifecycle(first_store)

    first.startup()
    first.mark_ready()

    shutdown = first.shutdown(exit_code=130)

    assert shutdown.clean is False
    assert shutdown.current_status == "stopped_unclean"

    second_store = RuntimeStateStore(db_path)
    second = RuntimeLifecycle(second_store)

    startup = second.startup()

    assert startup.previous_clean_shutdown is False
    assert startup.previous_status == "stopped_unclean"
    assert startup.current_status == "starting"

    second.mark_ready()

    diagnostics = RuntimeDiagnosticsChecker(
        runtime_store=second_store,
        learning_state=PersistentLearningState(second_store),
    ).check()

    assert diagnostics.runtime_status == "ready"
    assert diagnostics.clean_shutdown is False
    assert diagnostics.healthy is True


def test_runtime_value_recovery_quarantines_corrupted_value(tmp_path):
    store = RuntimeStateStore(tmp_path / "runtime_state.db")

    key = "runtime.corrupted.value"
    raw_value = json.dumps({"broken": True})

    store.set(key, raw_value)

    checker = RuntimeDiagnosticsChecker(
        runtime_store=store,
    )

    result = checker.recover_runtime_value(
        key,
        ValueError("invalid runtime value"),
    )

    assert result.recovered is True
    assert result.state_name == key
    assert result.quarantined_key.startswith(
        "recovery.quarantine."
    )

    assert store.get(key) is None
    assert store.value(result.quarantined_key) == raw_value
