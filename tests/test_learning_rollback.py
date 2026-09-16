from __future__ import annotations

import pytest

from experience.learning_regression import LearningRegressionDetector
from experience.learning_rollback import LearningRollbackPolicy


def make_regression(
    *,
    strategy="strategy-a",
    baseline=90.0,
    learned=90.0,
):
    detector = LearningRegressionDetector()
    return detector.detect(
        strategy=strategy,
        baseline_score=baseline,
        learned_score=learned,
    )


def test_no_regression_does_not_rollback():
    regression = make_regression(baseline=90.0, learned=92.0)

    decision = LearningRollbackPolicy().decide(regression)

    assert decision.rollback is False
    assert decision.severity == "none"


def test_low_regression_does_not_rollback_by_default():
    regression = make_regression(baseline=90.0, learned=82.0)

    decision = LearningRollbackPolicy().decide(regression)

    assert decision.rollback is False
    assert decision.severity == "low"


def test_medium_regression_does_not_rollback_by_default():
    regression = make_regression(baseline=90.0, learned=70.0)

    decision = LearningRollbackPolicy().decide(regression)

    assert decision.rollback is False
    assert decision.severity == "medium"


def test_high_regression_rolls_back_by_default():
    regression = make_regression(baseline=90.0, learned=50.0)

    decision = LearningRollbackPolicy().decide(regression)

    assert decision.rollback is True
    assert decision.severity == "high"


def test_low_threshold_can_trigger_rollback():
    regression = make_regression(baseline=90.0, learned=82.0)

    decision = LearningRollbackPolicy(
        rollback_severity="low",
    ).decide(regression)

    assert decision.rollback is True


def test_medium_threshold_triggers_for_medium_and_high():
    policy = LearningRollbackPolicy(
        rollback_severity="medium",
    )

    medium = policy.decide(
        make_regression(baseline=90.0, learned=70.0)
    )
    high = policy.decide(
        make_regression(baseline=90.0, learned=50.0)
    )

    assert medium.rollback is True
    assert high.rollback is True


def test_medium_threshold_does_not_trigger_for_low():
    policy = LearningRollbackPolicy(
        rollback_severity="medium",
    )

    decision = policy.decide(
        make_regression(baseline=90.0, learned=82.0)
    )

    assert decision.rollback is False


def test_invalid_policy_threshold():
    with pytest.raises(ValueError):
        LearningRollbackPolicy(rollback_severity="critical")


def test_empty_strategy_rejected():
    regression = make_regression(strategy="strategy-a")

    regression = regression.__class__(
        strategy=" ",
        baseline_score=regression.baseline_score,
        learned_score=regression.learned_score,
        regression=regression.regression,
        detected=regression.detected,
        severity=regression.severity,
        reason=regression.reason,
    )

    with pytest.raises(ValueError):
        LearningRollbackPolicy().decide(regression)


def test_decision_contains_reason():
    regression = make_regression(baseline=90.0, learned=50.0)

    decision = LearningRollbackPolicy().decide(regression)

    assert decision.reason
    assert "rollback threshold" in decision.reason
