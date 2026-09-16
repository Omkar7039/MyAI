import pytest

from experience.learning_effectiveness import (
    LearningEffectivenessEvaluator,
)


def test_learned_strategy_improves():
    result = LearningEffectivenessEvaluator().evaluate(
        baseline_score=60.0,
        learned_score=80.0,
    )

    assert result.baseline_score == 60.0
    assert result.learned_score == 80.0
    assert result.improvement == 20.0
    assert result.improved is True
    assert result.regression is False
    assert result.neutral is False
    assert result.confidence == 40.0


def test_learned_strategy_regresses():
    result = LearningEffectivenessEvaluator().evaluate(
        baseline_score=80.0,
        learned_score=60.0,
    )

    assert result.improvement == -20.0
    assert result.improved is False
    assert result.regression is True
    assert result.neutral is False
    assert result.confidence == 40.0


def test_equal_scores_are_neutral():
    result = LearningEffectivenessEvaluator().evaluate(
        baseline_score=75.0,
        learned_score=75.0,
    )

    assert result.improvement == 0.0
    assert result.improved is False
    assert result.regression is False
    assert result.neutral is True
    assert result.confidence == 0.0


def test_confidence_is_capped():
    result = LearningEffectivenessEvaluator().evaluate(
        baseline_score=0.0,
        learned_score=100.0,
    )

    assert result.confidence == 100.0


def test_small_improvement_is_detected():
    result = LearningEffectivenessEvaluator().evaluate(
        baseline_score=50.0,
        learned_score=50.5,
    )

    assert result.improved is True
    assert result.improvement == 0.5
    assert result.confidence == 1.0


def test_zero_boundary_scores_are_valid():
    result = LearningEffectivenessEvaluator().evaluate(
        baseline_score=0.0,
        learned_score=0.0,
    )

    assert result.neutral is True


def test_hundred_boundary_scores_are_valid():
    result = LearningEffectivenessEvaluator().evaluate(
        baseline_score=100.0,
        learned_score=100.0,
    )

    assert result.neutral is True


def test_invalid_baseline_score_is_rejected():
    with pytest.raises(
        ValueError,
        match="baseline_score must be between 0 and 100",
    ):
        LearningEffectivenessEvaluator().evaluate(
            baseline_score=-1.0,
            learned_score=50.0,
        )


def test_invalid_learned_score_is_rejected():
    with pytest.raises(
        ValueError,
        match="learned_score must be between 0 and 100",
    ):
        LearningEffectivenessEvaluator().evaluate(
            baseline_score=50.0,
            learned_score=101.0,
        )


def test_reasons_reflect_improvement():
    result = LearningEffectivenessEvaluator().evaluate(
        baseline_score=40.0,
        learned_score=90.0,
    )

    assert result.reasons == (
        "learned strategy outperformed the baseline",
    )


def test_reasons_reflect_regression():
    result = LearningEffectivenessEvaluator().evaluate(
        baseline_score=90.0,
        learned_score=40.0,
    )

    assert result.reasons == (
        "learned strategy underperformed the baseline",
    )


def test_reasons_reflect_neutral_result():
    result = LearningEffectivenessEvaluator().evaluate(
        baseline_score=50.0,
        learned_score=50.0,
    )

    assert result.reasons == (
        "learned strategy matched the baseline",
    )


def test_evaluation_is_deterministic():
    evaluator = LearningEffectivenessEvaluator()

    first = evaluator.evaluate(
        baseline_score=65.0,
        learned_score=85.0,
    )
    second = evaluator.evaluate(
        baseline_score=65.0,
        learned_score=85.0,
    )

    assert first == second
