import pytest

from experience.adaptive_strategy import AdaptiveStrategyRanker
from experience.learning_signal import LearningSignalCollector


def test_successful_strategy_gets_high_score():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix add",
            strategy="property",
            score=95.0,
        ),
        collector.verification_success(
            "verify add",
            strategy="property",
            score=90.0,
        ),
    ]

    result = AdaptiveStrategyRanker().rank(
        signals,
        {"property": 90.0},
    )

    assert len(result) == 1
    assert result[0].strategy == "property"
    assert result[0].success_rate == 100.0
    assert result[0].average_outcome_score == 92.5
    assert result[0].utility_score == 90.0
    assert result[0].failure_penalty == 0.0
    assert result[0].score == pytest.approx(95.75)


def test_failure_reduces_strategy_score():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix",
            strategy="standard",
            score=80.0,
        ),
        collector.repair_failure(
            "fix",
            strategy="standard",
            score=0.0,
        ),
    ]

    result = AdaptiveStrategyRanker().rank(
        signals,
        {"standard": 40.0},
    )

    assert result[0].success_rate == 50.0
    assert result[0].average_outcome_score == 40.0
    assert result[0].failure_penalty == 0.0
    assert result[0].score == pytest.approx(45.0)


def test_retry_and_rollback_create_penalty():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix",
            strategy="mutation",
            score=90.0,
        ),
        collector.retry(
            "fix",
            strategy="mutation",
        ),
        collector.rollback(
            "fix",
            strategy="mutation",
        ),
    ]

    result = AdaptiveStrategyRanker().rank(
        signals,
        {"mutation": 80.0},
    )

    assert result[0].failure_penalty == 10.0
    assert result[0].score == pytest.approx(83.0)


def test_utility_changes_ranking():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "a",
            strategy="standard",
            score=85.0,
        ),
        collector.repair_success(
            "b",
            strategy="property",
            score=70.0,
        ),
    ]

    result = AdaptiveStrategyRanker().rank(
        signals,
        {
            "standard": 30.0,
            "property": 100.0,
        },
    )

    assert result[0].strategy == "property"


def test_missing_utility_defaults_to_zero():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix",
            strategy="standard",
            score=80.0,
        ),
    ]

    result = AdaptiveStrategyRanker().rank(signals)

    assert result[0].utility_score == 0.0


def test_utility_is_clamped():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix",
            strategy="standard",
            score=80.0,
        ),
    ]

    high = AdaptiveStrategyRanker().rank(
        signals,
        {"standard": 500.0},
    )
    low = AdaptiveStrategyRanker().rank(
        signals,
        {"standard": -50.0},
    )

    assert high[0].utility_score == 100.0
    assert low[0].utility_score == 0.0


def test_negative_event_penalty_is_capped():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix",
            strategy="standard",
            score=100.0,
        ),
    ]

    signals.extend(
        [
            collector.retry("fix", strategy="standard")
            for _ in range(10)
        ]
    )

    result = AdaptiveStrategyRanker().rank(signals)

    assert result[0].failure_penalty == 20.0


def test_best_returns_top_strategy():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "a",
            strategy="standard",
            score=60.0,
        ),
        collector.repair_success(
            "b",
            strategy="property",
            score=95.0,
        ),
    ]

    best = AdaptiveStrategyRanker().best(
        signals,
        {
            "standard": 50.0,
            "property": 95.0,
        },
    )

    assert best is not None
    assert best.strategy == "property"


def test_empty_signals_return_empty_ranking():
    assert AdaptiveStrategyRanker().rank([]) == ()


def test_best_returns_none_for_empty_signals():
    assert AdaptiveStrategyRanker().best([]) is None


def test_strategy_names_are_normalized():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix",
            strategy="  PROPERTY  ",
            score=90.0,
        ),
    ]

    result = AdaptiveStrategyRanker().rank(signals)

    assert result[0].strategy == "property"


def test_ranking_is_deterministic():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "a",
            strategy="property",
            score=90.0,
        ),
        collector.repair_failure(
            "b",
            strategy="standard",
            score=0.0,
        ),
    ]

    ranker = AdaptiveStrategyRanker()

    first = ranker.rank(
        signals,
        {"property": 80.0},
    )
    second = ranker.rank(
        signals,
        {"property": 80.0},
    )

    assert first == second
