from __future__ import annotations

from experience.learning_control_benchmark import (
    LearningControlBenchmark,
)


def test_benchmark_has_five_cases():
    benchmark = LearningControlBenchmark()

    assert len(benchmark.cases()) == 5


def test_benchmark_case_names_are_unique():
    benchmark = LearningControlBenchmark()

    names = [case.name for case in benchmark.cases()]

    assert len(names) == len(set(names))


def test_benchmark_returns_one_result_per_case():
    benchmark = LearningControlBenchmark()

    results = benchmark.run()

    assert len(results) == len(benchmark.cases())


def test_all_benchmark_cases_pass():
    benchmark = LearningControlBenchmark()

    results = benchmark.run()

    assert all(result.passed for result in results)


def test_benchmark_is_green():
    assert LearningControlBenchmark().all_passed() is True


def test_safe_improvement_is_allowed():
    result = LearningControlBenchmark().run()[0]

    assert result.passed is True
    assert result.allowed is True
    assert result.rollback is False
    assert result.severity == "none"


def test_neutral_case_is_allowed():
    result = LearningControlBenchmark().run()[1]

    assert result.passed is True
    assert result.allowed is True
    assert result.rollback is False


def test_low_regression_is_allowed():
    result = LearningControlBenchmark().run()[2]

    assert result.passed is True
    assert result.allowed is True
    assert result.rollback is False
    assert result.severity == "low"


def test_high_regression_is_rolled_back():
    result = LearningControlBenchmark().run()[3]

    assert result.passed is True
    assert result.allowed is False
    assert result.rollback is True
    assert result.severity == "high"


def test_cross_task_learning_is_blocked():
    result = LearningControlBenchmark().run()[4]

    assert result.passed is True
    assert result.allowed is False
    assert result.rollback is False
    assert result.severity == "none"
