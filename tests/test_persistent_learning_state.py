from core.runtime_state import RuntimeStateStore
from experience.learning_approval import LearningApprovalDecision
from experience.learning_change_application import (
    LearningAppliedChange,
    LearningChangeApplication,
)
from experience.learning_change_proposal import LearningChangeProposal
from experience.persistent_learning_state import (
    PersistentLearningState,
)


def make_proposal(
    *,
    strategy="property",
    current=70.0,
    proposed=100.0,
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
        rationale="persistent state test",
    )


def make_approval(strategy="property"):
    return LearningApprovalDecision(
        approved=True,
        strategy=strategy,
        confidence=80.0,
        reason="approved",
    )


def test_persistent_state_round_trip(tmp_path):
    runtime = RuntimeStateStore(
        tmp_path / "runtime.db"
    )
    state = PersistentLearningState(runtime)

    change = LearningAppliedChange(
        strategy="property",
        previous_score=None,
        applied_score=100.0,
        observations=5,
        confidence=80.0,
    )

    state.save((change,))

    loaded = state.load()

    assert loaded == (change,)


def test_persistent_state_supports_multiple_strategies(
    tmp_path,
):
    runtime = RuntimeStateStore(
        tmp_path / "runtime.db"
    )
    state = PersistentLearningState(runtime)

    changes = (
        LearningAppliedChange(
            strategy="property",
            previous_score=None,
            applied_score=100.0,
            observations=5,
            confidence=80.0,
        ),
        LearningAppliedChange(
            strategy="mutation",
            previous_score=70.0,
            applied_score=95.0,
            observations=7,
            confidence=75.0,
        ),
    )

    state.save(changes)

    loaded = state.load()

    assert tuple(
        item.strategy
        for item in loaded
    ) == ("mutation", "property")

    assert loaded[0].applied_score == 95.0
    assert loaded[1].applied_score == 100.0


def test_learning_application_restores_persisted_state(
    tmp_path,
):
    db = tmp_path / "runtime.db"

    first_state = PersistentLearningState(
        RuntimeStateStore(db)
    )
    first_application = LearningChangeApplication(
        persistent_state=first_state,
    )

    proposal = make_proposal()
    approval = make_approval()

    applied = first_application.apply(
        proposal=proposal,
        approval=approval,
    )

    assert applied.applied_score == 100.0

    second_state = PersistentLearningState(
        RuntimeStateStore(db)
    )
    second_application = LearningChangeApplication(
        persistent_state=second_state,
    )

    restored = second_application.get("property")

    assert restored is not None
    assert restored.strategy == "property"
    assert restored.applied_score == 100.0
    assert restored.observations == 5
    assert restored.confidence == 80.0


def test_new_application_can_continue_from_restored_state(
    tmp_path,
):
    db = tmp_path / "runtime.db"

    first = LearningChangeApplication(
        persistent_state=PersistentLearningState(
            RuntimeStateStore(db)
        )
    )

    first.apply(
        proposal=make_proposal(
            current=70.0,
            proposed=90.0,
        ),
        approval=make_approval(),
    )

    second = LearningChangeApplication(
        persistent_state=PersistentLearningState(
            RuntimeStateStore(db)
        )
    )

    change = second.apply(
        proposal=make_proposal(
            current=90.0,
            proposed=100.0,
        ),
        approval=make_approval(),
    )

    assert change.previous_score == 90.0
    assert change.applied_score == 100.0


def test_clear_removes_persisted_governed_state(
    tmp_path,
):
    db = tmp_path / "runtime.db"

    application = LearningChangeApplication(
        persistent_state=PersistentLearningState(
            RuntimeStateStore(db)
        )
    )

    application.apply(
        proposal=make_proposal(),
        approval=make_approval(),
    )

    application.clear()

    restored = LearningChangeApplication(
        persistent_state=PersistentLearningState(
            RuntimeStateStore(db)
        )
    )

    assert restored.all() == ()


def test_missing_persistent_state_loads_empty(
    tmp_path,
):
    state = PersistentLearningState(
        RuntimeStateStore(
            tmp_path / "runtime.db"
        )
    )

    assert state.load() == ()


def test_clear_without_state_is_safe(tmp_path):
    state = PersistentLearningState(
        RuntimeStateStore(
            tmp_path / "runtime.db"
        )
    )

    state.clear()
    assert state.load() == ()


def test_rollback_history_survives_restart(
    tmp_path,
):
    db = tmp_path / "runtime.db"

    first = LearningChangeApplication(
        persistent_state=PersistentLearningState(
            RuntimeStateStore(db)
        )
    )

    first.apply(
        proposal=make_proposal(
            current=70.0,
            proposed=80.0,
        ),
        approval=make_approval(),
    )

    first.apply(
        proposal=make_proposal(
            current=80.0,
            proposed=90.0,
        ),
        approval=make_approval(),
    )

    second = LearningChangeApplication(
        persistent_state=PersistentLearningState(
            RuntimeStateStore(db)
        )
    )

    restored = second.rollback("property")

    assert restored is not None
    assert restored.applied_score == 80.0
    assert second.get("property") is not None
    assert second.get("property").applied_score == 80.0


def test_multiple_rollback_levels_survive_restart(
    tmp_path,
):
    db = tmp_path / "runtime.db"

    first = LearningChangeApplication(
        persistent_state=PersistentLearningState(
            RuntimeStateStore(db)
        )
    )

    for current, proposed in (
        (70.0, 80.0),
        (80.0, 90.0),
        (90.0, 95.0),
    ):
        first.apply(
            proposal=make_proposal(
                current=current,
                proposed=proposed,
            ),
            approval=make_approval(),
        )

    second = LearningChangeApplication(
        persistent_state=PersistentLearningState(
            RuntimeStateStore(db)
        )
    )

    first_restore = second.rollback("property")
    second_restore = second.rollback("property")
    third_restore = second.rollback("property")
    fourth_restore = second.rollback("property")

    assert first_restore is not None
    assert first_restore.applied_score == 90.0

    assert second_restore is not None
    assert second_restore.applied_score == 80.0

    assert third_restore is None
    assert fourth_restore is None

    assert second.get("property") is None


def test_rollback_persists_state_after_restart(
    tmp_path,
):
    db = tmp_path / "runtime.db"

    first = LearningChangeApplication(
        persistent_state=PersistentLearningState(
            RuntimeStateStore(db)
        )
    )

    first.apply(
        proposal=make_proposal(
            current=70.0,
            proposed=80.0,
        ),
        approval=make_approval(),
    )

    first.apply(
        proposal=make_proposal(
            current=80.0,
            proposed=90.0,
        ),
        approval=make_approval(),
    )

    restored = first.rollback("property")

    assert restored is not None
    assert restored.applied_score == 80.0

    second = LearningChangeApplication(
        persistent_state=PersistentLearningState(
            RuntimeStateStore(db)
        )
    )

    assert second.get("property") is not None
    assert second.get("property").applied_score == 80.0
