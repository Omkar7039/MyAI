from __future__ import annotations

from experience.learning_governance_benchmark import (
    LearningGovernanceBenchmark,
)


def test_benchmark_has_five_cases():
    benchmark = LearningGovernanceBenchmark()

    assert len(benchmark.cases()) == 5


def test_case_names_are_unique():
    benchmark = LearningGovernanceBenchmark()

    names = [case.name for case in benchmark.cases()]

    assert len(names) == len(set(names))


def test_run_returns_one_result_per_case():
    benchmark = LearningGovernanceBenchmark()

    results = benchmark.run()

    assert len(results) == 5


def test_all_cases_pass():
    benchmark = LearningGovernanceBenchmark()

    assert all(
        result.passed
        for result in benchmark.run()
    )


def test_benchmark_is_green():
    assert LearningGovernanceBenchmark().all_passed() is True


def test_strong_improvement_is_applied():
    result = LearningGovernanceBenchmark().run()[0]

    assert result.passed is True
    assert result.approved is True
    assert result.applied is True


def test_insufficient_observations_are_rejected():
    result = LearningGovernanceBenchmark().run()[1]

    assert result.passed is True
    assert result.approved is False
    assert result.applied is False


def test_neutral_outcome_is_rejected():
    result = LearningGovernanceBenchmark().run()[2]

    assert result.passed is True
    assert result.approved is False
    assert result.applied is False


def test_low_confidence_is_rejected():
    result = LearningGovernanceBenchmark().run()[3]

    assert result.passed is True
    assert result.approved is False
    assert result.applied is False


def test_regression_is_rejected():
    result = LearningGovernanceBenchmark().run()[4]

    assert result.passed is True
    assert result.approved is False
    assert result.applied is False
