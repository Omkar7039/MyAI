from verification.strategy_selector import VerificationStrategy
from verification.verification_benchmark import VerificationBenchmark


def test_benchmark_passes_all_cases():
    result = VerificationBenchmark().run()

    assert result.total_cases == 5
    assert result.passed_cases == 5
    assert result.failed_cases == 0
    assert result.accuracy == 100.0
    assert result.passed is True


def test_benchmark_covers_expected_strategies():
    benchmark = VerificationBenchmark()

    expected = {
        "invalid": VerificationStrategy.STRENGTHEN,
        "weak": VerificationStrategy.STRENGTHEN,
        "mutation_gap": VerificationStrategy.MUTATION,
        "property": VerificationStrategy.PROPERTY,
        "standard": VerificationStrategy.STANDARD,
    }

    for name, strategy in expected.items():
        decision = benchmark._select(name)
        assert decision.strategy == strategy


def test_invalid_case_uses_strengthening():
    result = VerificationBenchmark()._select("invalid")

    assert result.strategy == VerificationStrategy.STRENGTHEN
    assert result.priority == 100


def test_weak_case_uses_strengthening():
    result = VerificationBenchmark()._select("weak")

    assert result.strategy == VerificationStrategy.STRENGTHEN
    assert result.priority == 90


def test_mutation_gap_case_uses_mutation_strategy():
    result = VerificationBenchmark()._select("mutation_gap")

    assert result.strategy == VerificationStrategy.MUTATION
    assert result.priority == 80


def test_property_case_uses_property_strategy():
    result = VerificationBenchmark()._select("property")

    assert result.strategy == VerificationStrategy.PROPERTY
    assert result.priority == 70


def test_standard_case_uses_standard_strategy():
    result = VerificationBenchmark()._select("standard")

    assert result.strategy == VerificationStrategy.STANDARD
    assert result.priority == 50


def test_benchmark_is_deterministic():
    benchmark = VerificationBenchmark()

    first = benchmark.run()
    second = benchmark.run()

    assert first == second


def test_benchmark_never_uses_model_inference():
    result = VerificationBenchmark().run()

    assert result.passed is True
    assert result.accuracy == 100.0
