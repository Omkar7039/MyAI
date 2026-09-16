from __future__ import annotations

from experience.continuous_learning import ContinuousLearningController
from experience.learning_effectiveness_benchmark import (
    LearningEffectivenessBenchmark,
)


def test_benchmark_has_five_cases():
    benchmark = LearningEffectivenessBenchmark()

    assert len(benchmark.cases()) == 5


def test_benchmark_cases_have_unique_names():
    benchmark = LearningEffectivenessBenchmark()

    names = [case.name for case in benchmark.cases()]

    assert len(names) == len(set(names))


def test_benchmark_run_returns_one_result_per_case():
    benchmark = LearningEffectivenessBenchmark()

    results = benchmark.run()

    assert len(results) == len(benchmark.cases())


def test_benchmark_passes_all_cases():
    benchmark = LearningEffectivenessBenchmark()

    results = benchmark.run()

    assert all(result.passed for result in results)


def test_benchmark_all_passed():
    benchmark = LearningEffectivenessBenchmark()

    assert benchmark.all_passed() is True


def test_strong_improvement_case():
    benchmark = LearningEffectivenessBenchmark()

    result = benchmark.run()[0]

    assert result.passed is True
    assert result.improved is True
    assert result.regression_detected is False
    assert result.rollback is False


def test_neutral_case():
    benchmark = LearningEffectivenessBenchmark()

    result = benchmark.run()[2]

    assert result.passed is True
    assert result.improved is False
    assert result.regression_detected is False
    assert result.rollback is False


def test_medium_regression_case():
    benchmark = LearningEffectivenessBenchmark()

    result = benchmark.run()[3]

    assert result.passed is True
    assert result.improved is False
    assert result.regression_detected is True
    assert result.rollback is False


def test_high_regression_case():
    benchmark = LearningEffectivenessBenchmark()

    result = benchmark.run()[4]

    assert result.passed is True
    assert result.improved is False
    assert result.regression_detected is True
    assert result.rollback is True


def test_custom_controller_can_be_injected():
    controller = ContinuousLearningController(
        rollback_severity="medium",
    )
    benchmark = LearningEffectivenessBenchmark(controller)

    results = benchmark.run()

    assert results[3].rollback is True
    assert results[4].rollback is True
