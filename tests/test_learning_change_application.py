from __future__ import annotations

import pytest

from experience.learning_approval import (
    LearningApprovalDecision,
)
from experience.learning_change_application import (
    LearningChangeApplication,
)
from experience.learning_change_proposal import (
    LearningChangeProposal,
)


def make_proposal(**overrides):
    values = {
        "strategy": "property",
        "current_score": 70.0,
        "proposed_score": 90.0,
        "observations": 5,
        "improvement": 20.0,
        "improved": True,
        "regression_detected": False,
        "regression_severity": "none",
        "confidence": 80.0,
        "rationale": "learned strategy improved by 20.00 points",
    }

    values.update(overrides)

    return LearningChangeProposal(**values)


def make_approval(
    *,
    approved=True,
    strategy="property",
    confidence=80.0,
):
    return LearningApprovalDecision(
        approved=approved,
        strategy=strategy,
        confidence=confidence,
        reason="test approval",
    )


def test_approved_proposal_is_applied():
    application = LearningChangeApplication()

    change = application.apply(
        proposal=make_proposal(),
        approval=make_approval(),
    )

    assert change.strategy == "property"
    assert change.previous_score is None
    assert change.applied_score == 90.0
    assert change.observations == 5
    assert change.confidence == 80.0


def test_rejected_proposal_cannot_be_applied():
    application = LearningChangeApplication()

    with pytest.raises(
        ValueError,
        match="unapproved learning change",
    ):
        application.apply(
            proposal=make_proposal(),
            approval=make_approval(approved=False),
        )


def test_second_application_tracks_previous_score():
    application = LearningChangeApplication()

    first = application.apply(
        proposal=make_proposal(
            current_score=70.0,
            proposed_score=90.0,
        ),
        approval=make_approval(),
    )

    second = application.apply(
        proposal=make_proposal(
            current_score=90.0,
            proposed_score=95.0,
            improvement=5.0,
        ),
        approval=make_approval(confidence=85.0),
    )

    assert first.previous_score is None
    assert second.previous_score == 90.0
    assert second.applied_score == 95.0
    assert second.confidence == 85.0


def test_get_returns_applied_strategy():
    application = LearningChangeApplication()

    application.apply(
        proposal=make_proposal(),
        approval=make_approval(),
    )

    result = application.get("property")

    assert result is not None
    assert result.strategy == "property"
    assert result.applied_score == 90.0


def test_get_normalizes_strategy_whitespace():
    application = LearningChangeApplication()

    application.apply(
        proposal=make_proposal(),
        approval=make_approval(),
    )

    result = application.get("  property  ")

    assert result is not None
    assert result.strategy == "property"


def test_missing_strategy_returns_none():
    application = LearningChangeApplication()

    assert application.get("missing") is None


def test_all_returns_sorted_strategies():
    application = LearningChangeApplication()

    application.apply(
        proposal=make_proposal(strategy="zeta"),
        approval=make_approval(strategy="zeta"),
    )

    application.apply(
        proposal=make_proposal(strategy="alpha"),
        approval=make_approval(strategy="alpha"),
    )

    assert tuple(
        item.strategy
        for item in application.all()
    ) == ("alpha", "zeta")


def test_all_is_empty_initially():
    assert LearningChangeApplication().all() == ()


def test_clear_removes_all_state():
    application = LearningChangeApplication()

    application.apply(
        proposal=make_proposal(),
        approval=make_approval(),
    )

    application.clear()

    assert application.all() == ()
    assert application.get("property") is None


def test_strategy_mismatch_is_rejected():
    application = LearningChangeApplication()

    with pytest.raises(
        ValueError,
        match="strategies must match",
    ):
        application.apply(
            proposal=make_proposal(strategy="property"),
            approval=make_approval(strategy="mutation"),
        )


def test_empty_strategy_is_rejected():
    application = LearningChangeApplication()

    with pytest.raises(
        ValueError,
        match="strategy must not be empty",
    ):
        application.apply(
            proposal=make_proposal(strategy=" "),
            approval=make_approval(strategy=" "),
        )


def test_state_is_replaced_for_same_strategy():
    application = LearningChangeApplication()

    application.apply(
        proposal=make_proposal(
            proposed_score=85.0,
            improvement=15.0,
        ),
        approval=make_approval(),
    )

    application.apply(
        proposal=make_proposal(
            current_score=85.0,
            proposed_score=95.0,
            improvement=10.0,
        ),
        approval=make_approval(),
    )

    result = application.get("property")

    assert result is not None
    assert result.applied_score == 95.0
    assert result.previous_score == 85.0


def test_application_is_deterministic():
    proposal = make_proposal()
    approval = make_approval()

    first = LearningChangeApplication().apply(
        proposal=proposal,
        approval=approval,
    )

    second = LearningChangeApplication().apply(
        proposal=proposal,
        approval=approval,
    )

    assert first == second


def test_all_returns_immutable_snapshot():
    application = LearningChangeApplication()

    application.apply(
        proposal=make_proposal(),
        approval=make_approval(),
    )

    snapshot = application.all()

    assert isinstance(snapshot, tuple)


def test_first_application_can_be_rolled_back():
    application = LearningChangeApplication()

    application.apply(
        proposal=make_proposal(),
        approval=make_approval(),
    )

    assert application.can_rollback("property") is True

    previous = application.rollback("property")

    assert previous is None
    assert application.get("property") is None
    assert application.all() == ()
    assert application.can_rollback("property") is False


def test_second_application_rolls_back_to_previous_state():
    application = LearningChangeApplication()

    application.apply(
        proposal=make_proposal(
            proposed_score=90.0,
            improvement=20.0,
        ),
        approval=make_approval(),
    )

    application.apply(
        proposal=make_proposal(
            current_score=90.0,
            proposed_score=95.0,
            improvement=5.0,
        ),
        approval=make_approval(),
    )

    restored = application.rollback("property")

    assert restored is not None
    assert restored.applied_score == 90.0

    current = application.get("property")

    assert current is not None
    assert current.applied_score == 90.0
    assert current.previous_score is None


def test_multiple_rollbacks_restore_states_in_reverse_order():
    application = LearningChangeApplication()

    for current, proposed, improvement in (
        (70.0, 80.0, 10.0),
        (80.0, 90.0, 10.0),
        (90.0, 95.0, 5.0),
    ):
        application.apply(
            proposal=make_proposal(
                current_score=current,
                proposed_score=proposed,
                improvement=improvement,
            ),
            approval=make_approval(),
        )

    first_restore = application.rollback("property")
    second_restore = application.rollback("property")
    third_restore = application.rollback("property")
    fourth_restore = application.rollback("property")

    assert first_restore is not None
    assert first_restore.applied_score == 90.0

    assert second_restore is not None
    assert second_restore.applied_score == 80.0

    assert third_restore is None
    assert fourth_restore is None

    assert application.get("property") is None


def test_rollback_missing_strategy_is_safe():
    application = LearningChangeApplication()

    assert application.rollback("missing") is None


def test_rollback_strategy_is_normalized():
    application = LearningChangeApplication()

    application.apply(
        proposal=make_proposal(),
        approval=make_approval(),
    )

    application.rollback("  property  ")

    assert application.get("property") is None


def test_empty_rollback_strategy_is_rejected():
    with pytest.raises(
        ValueError,
        match="strategy must not be empty",
    ):
        LearningChangeApplication().rollback(" ")


def test_can_rollback_empty_strategy_is_rejected():
    with pytest.raises(
        ValueError,
        match="strategy must not be empty",
    ):
        LearningChangeApplication().can_rollback(" ")


def test_clear_removes_rollback_history():
    application = LearningChangeApplication()

    application.apply(
        proposal=make_proposal(),
        approval=make_approval(),
    )

    assert application.can_rollback("property") is True

    application.clear()

    assert application.can_rollback("property") is False
    assert application.rollback("property") is None


def test_rollback_does_not_affect_other_strategies():
    application = LearningChangeApplication()

    application.apply(
        proposal=make_proposal(strategy="property"),
        approval=make_approval(strategy="property"),
    )

    application.apply(
        proposal=make_proposal(strategy="mutation"),
        approval=make_approval(strategy="mutation"),
    )

    application.rollback("property")

    assert application.get("property") is None
    assert application.get("mutation") is not None
    assert application.get("mutation").applied_score == 90.0


def test_rollback_is_deterministic():
    def run():
        application = LearningChangeApplication()

        application.apply(
            proposal=make_proposal(
                proposed_score=90.0,
                improvement=20.0,
            ),
            approval=make_approval(),
        )

        application.apply(
            proposal=make_proposal(
                current_score=90.0,
                proposed_score=95.0,
                improvement=5.0,
            ),
            approval=make_approval(),
        )

        restored = application.rollback("property")
        current = application.get("property")

        return restored, current

    first = run()
    second = run()

    assert first == second
