from experience.automatic_learning_rollback import (
    AutomaticLearningRollback,
)
from experience.continuous_learning import ContinuousLearningController
from experience.learning_approval import LearningApprovalDecision
from experience.learning_change_application import (
    LearningChangeApplication,
)
from experience.learning_change_proposal import LearningChangeProposal


def make_proposal(
    *,
    strategy="property",
    current_score=70.0,
    proposed_score=90.0,
):
    return LearningChangeProposal(
        strategy=strategy,
        current_score=current_score,
        proposed_score=proposed_score,
        observations=5,
        improvement=proposed_score - current_score,
        improved=proposed_score > current_score,
        regression_detected=False,
        regression_severity="none",
        confidence=80.0,
        rationale="test change",
    )


def apply_change(application, proposal):
    approval = LearningApprovalDecision(
        approved=True,
        strategy=proposal.strategy,
        confidence=80.0,
        reason="approved",
    )

    return application.apply(
        proposal=proposal,
        approval=approval,
    )


def test_improvement_does_not_trigger_rollback():
    application = LearningChangeApplication()
    proposal = make_proposal()
    applied = apply_change(application, proposal)

    rollback = AutomaticLearningRollback(
        application=application,
    )

    result = rollback.evaluate(
        strategy="property",
        baseline_score=70.0,
        learned_score=90.0,
    )

    assert applied.applied_score == 90.0
    assert result.rollback_requested is False
    assert result.rolled_back is False
    assert result.restored is None
    assert application.get("property") is not None
    assert application.get("property").applied_score == 90.0


def test_high_regression_automatically_rolls_back():
    application = LearningChangeApplication()

    first = make_proposal(
        current_score=70.0,
        proposed_score=90.0,
    )
    second = make_proposal(
        current_score=90.0,
        proposed_score=95.0,
    )

    apply_change(application, first)
    latest = apply_change(application, second)

    rollback = AutomaticLearningRollback(
        application=application,
    )

    result = rollback.evaluate(
        strategy="property",
        baseline_score=95.0,
        learned_score=40.0,
    )

    assert result.rollback_requested is True
    assert result.rolled_back is True
    assert result.severity == "high"
    assert result.restored is not None
    assert result.restored.applied_score == 90.0
    assert latest.applied_score == 95.0
    assert application.get("property").applied_score == 90.0


def test_rollback_is_not_performed_without_history():
    application = LearningChangeApplication()

    rollback = AutomaticLearningRollback(
        application=application,
    )

    result = rollback.evaluate(
        strategy="property",
        baseline_score=90.0,
        learned_score=40.0,
    )

    assert result.rollback_requested is True
    assert result.rolled_back is False
    assert result.restored is None
    assert "no rollback state is available" in result.reason
    assert application.get("property") is None


def test_custom_medium_threshold_rolls_back():
    application = LearningChangeApplication()

    proposal = make_proposal(
        current_score=70.0,
        proposed_score=90.0,
    )
    apply_change(application, proposal)

    rollback = AutomaticLearningRollback(
        controller=ContinuousLearningController(
            rollback_severity="medium",
        ),
        application=application,
    )

    result = rollback.evaluate(
        strategy="property",
        baseline_score=90.0,
        learned_score=70.0,
    )

    assert result.rollback_requested is True
    assert result.rolled_back is True
    assert result.restored is None
    assert application.get("property") is None


def test_strategy_name_is_normalized():
    application = LearningChangeApplication()

    proposal = make_proposal(
        strategy="property",
    )
    apply_change(application, proposal)

    rollback = AutomaticLearningRollback(
        application=application,
    )

    result = rollback.evaluate(
        strategy="  PROPERTY  ",
        baseline_score=90.0,
        learned_score=40.0,
    )

    assert result.strategy == "property"
    assert result.rollback_requested is True
    assert result.rolled_back is True


def test_empty_strategy_is_rejected():
    rollback = AutomaticLearningRollback()

    try:
        rollback.evaluate(
            strategy=" ",
            baseline_score=70.0,
            learned_score=40.0,
        )
    except ValueError as exc:
        assert str(exc) == "strategy must not be empty"
    else:
        raise AssertionError("expected ValueError")
