from __future__ import annotations

from experience.continuous_learning import ContinuousLearningController
from experience.learning_effectiveness import LearningEffectivenessEvaluator
from experience.learning_effectiveness_aggregate import (
    LearningEffectivenessAggregator,
)
from experience.learning_effectiveness_benchmark import (
    LearningEffectivenessBenchmark,
)
from experience.learning_regression import LearningRegressionDetector
from experience.learning_rollback import LearningRollbackPolicy


def test_full_effectiveness_evaluation_pipeline():
    comparisons = (
        (60.0, 90.0),
        (70.0, 85.0),
        (75.0, 90.0),
        (80.0, 95.0),
    )

    aggregate = LearningEffectivenessAggregator().aggregate(comparisons)

    assert aggregate.total_observations == 4
    assert aggregate.improvement_rate == 100.0
    assert aggregate.average_improvement > 0.0
    assert aggregate.consistently_improving is True


def test_effectiveness_detects_neutral_outcome():
    evaluator = LearningEffectivenessEvaluator()

    result = evaluator.evaluate(
        baseline_score=80.0,
        learned_score=80.0,
    )

    assert result.improved is False
    assert result.regression is False
    assert result.improvement == 0.0


def test_effectiveness_detects_regression():
    evaluator = LearningEffectivenessEvaluator()

    result = evaluator.evaluate(
        baseline_score=90.0,
        learned_score=65.0,
    )

    assert result.improved is False
    assert result.regression is True
    assert result.improvement == -25.0


def test_regression_detection_and_rollback():
    detector = LearningRegressionDetector()

    regression = detector.detect(
        strategy="strategy-a",
        baseline_score=90.0,
        learned_score=45.0,
    )

    assert regression.detected is True
    assert regression.severity == "high"
    assert regression.regression == 45.0

    rollback = LearningRollbackPolicy().decide(regression)

    assert rollback.rollback is True


def test_continuous_controller_accepts_improvement():
    controller = ContinuousLearningController()

    decision = controller.evaluate(
        strategy="strategy-a",
        baseline_score=65.0,
        learned_score=92.0,
    )

    assert decision.improved is True
    assert decision.regression_detected is False
    assert decision.rollback is False
    assert decision.severity == "none"


def test_continuous_controller_rolls_back_high_regression():
    controller = ContinuousLearningController()

    decision = controller.evaluate(
        strategy="strategy-a",
        baseline_score=95.0,
        learned_score=40.0,
    )

    assert decision.improved is False
    assert decision.regression_detected is True
    assert decision.rollback is True
    assert decision.severity == "high"


def test_full_benchmark_is_green():
    benchmark = LearningEffectivenessBenchmark()

    results = benchmark.run()

    assert len(results) == 5
    assert all(result.passed for result in results)
    assert benchmark.all_passed() is True
