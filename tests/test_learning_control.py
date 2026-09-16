from __future__ import annotations

import pytest

from experience.continuous_learning import ContinuousLearningController
from experience.learning_control import LearningControlAdapter


def test_improved_learning_is_allowed():
    decision = LearningControlAdapter().evaluate(
        strategy="strategy-a",
        baseline_score=70.0,
        learned_score=90.0,
    )

    assert decision.allowed is True
    assert decision.rollback is False
    assert decision.improved is True
    assert decision.regression_detected is False
    assert decision.severity == "none"


def test_neutral_learning_is_allowed():
    decision = LearningControlAdapter().evaluate(
        strategy="strategy-a",
        baseline_score=80.0,
        learned_score=80.0,
    )

    assert decision.allowed is True
    assert decision.rollback is False
    assert decision.improved is False
    assert decision.regression_detected is False


def test_low_regression_remains_allowed():
    decision = LearningControlAdapter().evaluate(
        strategy="strategy-a",
        baseline_score=90.0,
        learned_score=82.0,
    )

    assert decision.allowed is True
    assert decision.rollback is False
    assert decision.regression_detected is True
    assert decision.severity == "low"


def test_medium_regression_remains_allowed_by_default():
    decision = LearningControlAdapter().evaluate(
        strategy="strategy-a",
        baseline_score=90.0,
        learned_score=70.0,
    )

    assert decision.allowed is True
    assert decision.rollback is False
    assert decision.severity == "medium"


def test_high_regression_is_blocked():
    decision = LearningControlAdapter().evaluate(
        strategy="strategy-a",
        baseline_score=90.0,
        learned_score=40.0,
    )

    assert decision.allowed is False
    assert decision.rollback is True
    assert decision.regression_detected is True
    assert decision.severity == "high"


def test_custom_controller_is_supported():
    controller = ContinuousLearningController(
        rollback_severity="medium",
    )
    adapter = LearningControlAdapter(controller)

    decision = adapter.evaluate(
        strategy="strategy-a",
        baseline_score=90.0,
        learned_score=70.0,
    )

    assert decision.allowed is False
    assert decision.rollback is True
    assert decision.severity == "medium"


@pytest.mark.parametrize(
    ("baseline", "learned"),
    [
        (-1.0, 80.0),
        (101.0, 80.0),
        (80.0, -1.0),
        (80.0, 101.0),
    ],
)
def test_invalid_scores_are_rejected(baseline, learned):
    with pytest.raises(ValueError):
        LearningControlAdapter().evaluate(
            strategy="strategy-a",
            baseline_score=baseline,
            learned_score=learned,
        )


def test_empty_strategy_is_rejected():
    with pytest.raises(ValueError):
        LearningControlAdapter().evaluate(
            strategy=" ",
            baseline_score=80.0,
            learned_score=90.0,
        )


def test_reason_is_preserved():
    decision = LearningControlAdapter().evaluate(
        strategy="strategy-a",
        baseline_score=90.0,
        learned_score=40.0,
    )

    assert decision.reason
