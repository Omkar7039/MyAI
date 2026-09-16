from experience.learning_integration_benchmark import (
    LearningIntegrationBenchmark,
)


def test_integration_benchmark_passes():
    result = LearningIntegrationBenchmark().run()

    assert result.total_cases == 4
    assert result.passed_cases == 4
    assert result.failed_cases == 0
    assert result.accuracy == 100.0
    assert result.passed is True


def test_strong_property_case_learns():
    result = LearningIntegrationBenchmark()._evaluate(
        "strong_property"
    )

    assert result == (True, "property")


def test_insufficient_case_falls_back():
    result = LearningIntegrationBenchmark()._evaluate(
        "insufficient"
    )

    assert result == (False, "standard")


def test_failed_strategy_is_not_learned():
    result = LearningIntegrationBenchmark()._evaluate(
        "failed_standard"
    )

    assert result == (False, "property")


def test_fallback_case_uses_default():
    result = LearningIntegrationBenchmark()._evaluate(
        "fallback"
    )

    assert result == (False, "standard")


def test_benchmark_cases_are_unique():
    cases = LearningIntegrationBenchmark()._cases()

    assert len(cases) == 4
    assert len({case.name for case in cases}) == 4


def test_benchmark_is_deterministic():
    benchmark = LearningIntegrationBenchmark()

    first = benchmark.run()
    second = benchmark.run()

    assert first == second
