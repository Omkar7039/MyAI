from core.runtime_state import RuntimeStateStore
from experience.learning_approval import LearningApprovalDecision
from experience.learning_change_application import (
    LearningChangeApplication,
)
from experience.learning_change_proposal import LearningChangeProposal
from experience.learning_state_retention import (
    LearningStateRetentionManager,
)
from experience.persistent_learning_state import (
    PersistentLearningState,
)


def make_proposal(
    *,
    current,
    proposed,
    strategy="property",
):
    return LearningChangeProposal(
        strategy=strategy,
        current_score=current,
        proposed_score=proposed,
        observations=5,
        improvement=proposed - current,
        improved=proposed > current,
        regression_detected=False,
        regression_severity="none",
        confidence=80.0,
        rationale="retention test",
    )


def make_approval(strategy="property"):
    return LearningApprovalDecision(
        approved=True,
        strategy=strategy,
        confidence=80.0,
        reason="approved",
    )


def make_application(tmp_path):
    state = PersistentLearningState(
        RuntimeStateStore(
            tmp_path / "runtime.db"
        )
    )

    return (
        LearningChangeApplication(
            persistent_state=state,
        ),
        state,
    )


def add_change(
    application,
    current,
    proposed,
):
    return application.apply(
        proposal=make_proposal(
            current=current,
            proposed=proposed,
        ),
        approval=make_approval(),
    )


def test_retention_dry_run_does_not_modify_state(tmp_path):
    application, state = make_application(tmp_path)

    add_change(application, 70.0, 80.0)
    add_change(application, 80.0, 90.0)
    add_change(application, 90.0, 95.0)

    before = state.load_with_history()

    report = LearningStateRetentionManager(
        state,
        max_rollback_entries=1,
    ).run(
        apply=False,
    )

    after = state.load_with_history()

    assert report.applied is False
    assert report.scanned_strategies == 1
    assert report.pruned_entries == 2
    assert before == after


def test_retention_prunes_oldest_entries_when_applied(
    tmp_path,
):
    application, state = make_application(tmp_path)

    add_change(application, 70.0, 80.0)
    add_change(application, 80.0, 90.0)
    add_change(application, 90.0, 95.0)
    add_change(application, 95.0, 100.0)

    report = LearningStateRetentionManager(
        state,
        max_rollback_entries=2,
    ).run(
        apply=True,
    )

    assert report.applied is True
    assert report.pruned_entries == 2

    _, history = state.load_with_history()

    assert len(history["property"]) == 2


def test_active_strategy_is_always_retained(tmp_path):
    application, state = make_application(tmp_path)

    active = add_change(
        application,
        70.0,
        100.0,
    )

    LearningStateRetentionManager(
        state,
        max_rollback_entries=0,
    ).run(
        apply=True,
    )

    restored_changes, history = state.load_with_history()

    assert len(restored_changes) == 1
    assert restored_changes[0] == active
    assert history["property"] == []


def test_zero_retention_removes_all_rollback_history(
    tmp_path,
):
    application, state = make_application(tmp_path)

    add_change(application, 70.0, 80.0)
    add_change(application, 80.0, 90.0)
    add_change(application, 90.0, 100.0)

    report = LearningStateRetentionManager(
        state,
        max_rollback_entries=0,
    ).run(
        apply=True,
    )

    assert report.pruned_entries == 3

    changes, history = state.load_with_history()

    assert len(changes) == 1
    assert changes[0].applied_score == 100.0
    assert history["property"] == []


def test_retention_preserves_other_strategies(tmp_path):
    application, state = make_application(tmp_path)

    add_change(application, 70.0, 80.0)
    add_change(application, 80.0, 90.0)

    application.apply(
        proposal=make_proposal(
            strategy="mutation",
            current=70.0,
            proposed=95.0,
        ),
        approval=make_approval(
            strategy="mutation",
        ),
    )

    report = LearningStateRetentionManager(
        state,
        max_rollback_entries=0,
    ).run(
        apply=True,
    )

    assert report.scanned_strategies == 2

    changes, history = state.load_with_history()

    assert tuple(
        item.strategy
        for item in changes
    ) == ("mutation", "property")

    assert history["property"] == []
    assert history["mutation"] == []


def test_empty_history_is_safe(tmp_path):
    _, state = make_application(tmp_path)

    report = LearningStateRetentionManager(
        state,
        max_rollback_entries=2,
    ).run(
        apply=True,
    )

    assert report.scanned_strategies == 0
    assert report.retained_entries == 0
    assert report.pruned_entries == 0


def test_negative_retention_limit_is_rejected(tmp_path):
    _, state = make_application(tmp_path)

    try:
        LearningStateRetentionManager(
            state,
            max_rollback_entries=-1,
        )
    except ValueError as exc:
        assert str(exc) == (
            "max_rollback_entries must be >= 0"
        )
    else:
        raise AssertionError("expected ValueError")
