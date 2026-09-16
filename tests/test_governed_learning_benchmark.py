from experience.governed_learning_benchmark import (
    GovernedLearningBenchmark,
)


def test_governed_learning_benchmark():
    benchmark = GovernedLearningBenchmark()

    results = benchmark.run()

    assert len(results) == 5
    assert all(result.passed for result in results)


def test_governed_learning_benchmark_is_deterministic():
    benchmark = GovernedLearningBenchmark()

    first = benchmark.run()
    second = benchmark.run()

    assert first == second
