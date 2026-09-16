from experience.learning_benchmark import LearningBenchmark


def test_learning_benchmark_passes():
    result = LearningBenchmark().run()

    assert result.total_cases == 5
    assert result.passed_cases == 5
    assert result.failed_cases == 0
    assert result.accuracy == 100.0
    assert result.passed is True


def test_strong_history_is_allowed():
    result = LearningBenchmark()._evaluate(
        "strong_history"
    )

    assert result.allowed is True
    assert result.strategy == "property"


def test_insufficient_history_is_blocked():
    result = LearningBenchmark()._evaluate(
        "insufficient_history"
    )

    assert result.allowed is False
    assert result.strategy == "property"


def test_weak_strategy_is_blocked():
    result = LearningBenchmark()._evaluate(
        "weak_strategy"
    )

    assert result.allowed is False
    assert result.strategy == "standard"


def test_penalized_strategy_can_still_be_allowed():
    result = LearningBenchmark()._evaluate(
        "successful_but_penalized"
    )

    assert result.allowed is True
    assert result.strategy == "mutation"


def test_standard_fallback_is_allowed():
    result = LearningBenchmark()._evaluate(
        "standard_fallback"
    )

    assert result.allowed is True
    assert result.strategy == "standard"


def test_benchmark_is_deterministic():
    benchmark = LearningBenchmark()

    first = benchmark.run()
    second = benchmark.run()

    assert first == second


def test_benchmark_has_full_coverage():
    benchmark = LearningBenchmark()

    cases = benchmark._cases()

    assert len(cases) == 5
    assert len({case.name for case in cases}) == 5
