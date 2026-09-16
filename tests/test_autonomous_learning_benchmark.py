from experience.autonomous_learning_benchmark import (
    AutonomousLearningBenchmark,
)


def test_benchmark_passes_all_cases():
    result = AutonomousLearningBenchmark().run()

    assert result.total_cases == 4
    assert result.passed_cases == 4
    assert result.failed_cases == 0
    assert result.accuracy == 100.0
    assert result.passed is True


def test_strong_property_history_is_learned():
    result = AutonomousLearningBenchmark()._evaluate(
        "strong_property"
    )

    assert result == (True, "property")


def test_insufficient_history_falls_back():
    result = AutonomousLearningBenchmark()._evaluate(
        "insufficient"
    )

    assert result == (False, "standard")


def test_unrelated_task_family_is_isolated():
    result = AutonomousLearningBenchmark()._evaluate(
        "isolated_family"
    )

    assert result == (False, "standard")


def test_fallback_case_uses_default():
    result = AutonomousLearningBenchmark()._evaluate(
        "fallback"
    )

    assert result == (False, "standard")


def test_cases_are_unique():
    cases = AutonomousLearningBenchmark()._cases()

    assert len(cases) == 4
    assert len({case.name for case in cases}) == 4


def test_benchmark_is_deterministic():
    benchmark = AutonomousLearningBenchmark()

    first = benchmark.run()
    second = benchmark.run()

    assert first == second
