from __future__ import annotations

import pytest

from experience.continuous_learning import ContinuousLearningController


def test_improvement_is_accepted_without_rollback():
    decision = ContinuousLearningController().evaluate(
        strategy="strategy-a",
        baseline_score=70.0,
        learned_score=85.0,
    )

    assert decision.improved is True
    assert decision.regression_detected is False
    assert decision.rollback is False
    assert decision.severity == "none"


def test_neutral_result_is_not_rollback():
    decision = ContinuousLearningController().evaluate(
        strategy="strategy-a",
        baseline_score=80.0,
        learned_score=80.0,
    )

    assert decision.improved is False
    assert decision.regression_detected is False
    assert decision.rollback is False


def test_low_regression_is_detected_but_not_rolled_back():
    decision = ContinuousLearningController().evaluate(
        strategy="strategy-a",
        baseline_score=90.0,
        learned_score=82.0,
    )

    assert decision.improved is False
    assert decision.regression_detected is True
    assert decision.rollback is False
    assert decision.severity == "low"


def test_medium_regression_is_detected_but_not_rolled_back_by_default():
    decision = ContinuousLearningController().evaluate(
        strategy="strategy-a",
        baseline_score=90.0,
        learned_score=70.0,
    )

    assert decision.regression_detected is True
    assert decision.rollback is False
    assert decision.severity == "medium"


def test_high_regression_triggers_rollback():
    decision = ContinuousLearningController().evaluate(
        strategy="strategy-a",
        baseline_score=90.0,
        learned_score=50.0,
    )

    assert decision.regression_detected is True
    assert decision.rollback is True
    assert decision.severity == "high"


def test_custom_medium_rollback_threshold():
    controller = ContinuousLearningController(
        rollback_severity="medium",
    )

    decision = controller.evaluate(
        strategy="strategy-a",
        baseline_score=90.0,
        learned_score=70.0,
    )

    assert decision.rollback is True


def test_custom_low_regression_threshold():
    controller = ContinuousLearningController(
        low_regression_threshold=5.0,
        medium_regression_threshold=15.0,
    )

    decision = controller.evaluate(
        strategy="strategy-a",
        baseline_score=90.0,
        learned_score=82.0,
    )

    assert decision.severity == "medium"
    assert decision.rollback is False


def test_invalid_strategy_rejected():
    with pytest.raises(ValueError):
        ContinuousLearningController().evaluate(
            strategy=" ",
            baseline_score=80.0,
            learned_score=90.0,
        )


@pytest.mark.parametrize(
    ("field", "baseline", "learned"),
    [
        ("baseline", -1.0, 80.0),
        ("baseline", 101.0, 80.0),
        ("learned", 80.0, -1.0),
        ("learned", 80.0, 101.0),
    ],
)
def test_scores_must_be_in_range(field, baseline, learned):
    with pytest.raises(ValueError, match=field):
        ContinuousLearningController().evaluate(
            strategy="strategy-a",
            baseline_score=baseline,
            learned_score=learned,
        )


def test_reason_is_present():
    decision = ContinuousLearningController().evaluate(
        strategy="strategy-a",
        baseline_score=90.0,
        learned_score=50.0,
    )

    assert decision.reason
