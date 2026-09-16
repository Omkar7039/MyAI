import pytest

from experience.learning_regression import (
    LearningRegressionDetector,
)


def test_no_regression_is_detected():
    result = LearningRegressionDetector().detect(
        strategy="property",
        baseline_score=70.0,
        learned_score=80.0,
    )

    assert result.detected is False
    assert result.regression == -10.0
    assert result.severity == "none"


def test_equal_scores_are_not_regression():
    result = LearningRegressionDetector().detect(
        strategy="property",
        baseline_score=80.0,
        learned_score=80.0,
    )

    assert result.detected is False
    assert result.regression == 0.0
    assert result.severity == "none"


def test_small_regression_is_low():
    result = LearningRegressionDetector().detect(
        strategy="property",
        baseline_score=80.0,
        learned_score=75.0,
    )

    assert result.detected is True
    assert result.regression == 5.0
    assert result.severity == "low"


def test_medium_regression_is_medium():
    result = LearningRegressionDetector().detect(
        strategy="property",
        baseline_score=90.0,
        learned_score=70.0,
    )

    assert result.detected is True
    assert result.regression == 20.0
    assert result.severity == "medium"


def test_large_regression_is_high():
    result = LearningRegressionDetector().detect(
        strategy="property",
        baseline_score=90.0,
        learned_score=50.0,
    )

    assert result.detected is True
    assert result.regression == 40.0
    assert result.severity == "high"


def test_low_threshold_boundary():
    result = LearningRegressionDetector(
        low_threshold=10.0,
        medium_threshold=25.0,
    ).detect(
        strategy="standard",
        baseline_score=80.0,
        learned_score=70.0,
    )

    assert result.detected is True
    assert result.severity == "low"


def test_medium_threshold_boundary():
    result = LearningRegressionDetector(
        low_threshold=10.0,
        medium_threshold=25.0,
    ).detect(
        strategy="standard",
        baseline_score=80.0,
        learned_score=55.0,
    )

    assert result.detected is True
    assert result.severity == "medium"


def test_just_above_medium_threshold_is_high():
    result = LearningRegressionDetector(
        low_threshold=10.0,
        medium_threshold=25.0,
    ).detect(
        strategy="standard",
        baseline_score=80.0,
        learned_score=54.9,
    )

    assert result.detected is True
    assert result.severity == "high"


def test_strategy_is_trimmed():
    result = LearningRegressionDetector().detect(
        strategy="  mutation  ",
        baseline_score=80.0,
        learned_score=70.0,
    )

    assert result.strategy == "mutation"


def test_empty_strategy_is_rejected():
    with pytest.raises(
        ValueError,
        match="strategy must not be empty",
    ):
        LearningRegressionDetector().detect(
            strategy="   ",
            baseline_score=80.0,
            learned_score=70.0,
        )


def test_invalid_baseline_score_is_rejected():
    with pytest.raises(
        ValueError,
        match="baseline_score must be between 0 and 100",
    ):
        LearningRegressionDetector().detect(
            strategy="property",
            baseline_score=-1.0,
            learned_score=50.0,
        )


def test_invalid_learned_score_is_rejected():
    with pytest.raises(
        ValueError,
        match="learned_score must be between 0 and 100",
    ):
        LearningRegressionDetector().detect(
            strategy="property",
            baseline_score=50.0,
            learned_score=101.0,
        )


def test_invalid_low_threshold_is_rejected():
    with pytest.raises(
        ValueError,
        match="low_threshold must be greater than 0",
    ):
        LearningRegressionDetector(
            low_threshold=0.0,
        )


def test_invalid_medium_threshold_is_rejected():
    with pytest.raises(
        ValueError,
        match="medium_threshold must be greater than low_threshold",
    ):
        LearningRegressionDetector(
            low_threshold=10.0,
            medium_threshold=10.0,
        )


def test_reason_contains_regression_amount():
    result = LearningRegressionDetector().detect(
        strategy="property",
        baseline_score=90.0,
        learned_score=75.0,
    )

    assert result.reason == (
        "learned strategy regressed by 15.00 points"
    )


def test_detection_is_deterministic():
    detector = LearningRegressionDetector()

    first = detector.detect(
        strategy="property",
        baseline_score=90.0,
        learned_score=70.0,
    )
    second = detector.detect(
        strategy="property",
        baseline_score=90.0,
        learned_score=70.0,
    )

    assert first == second
