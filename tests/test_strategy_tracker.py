from experience.learning_signal import LearningSignalCollector
from experience.strategy_tracker import SuccessfulStrategyTracker


def test_summarizes_successful_strategy():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix add",
            strategy="standard",
            score=90.0,
        ),
        collector.repair_success(
            "fix parser",
            strategy="standard",
            score=80.0,
        ),
    ]

    result = SuccessfulStrategyTracker().summarize(signals)

    assert len(result) == 1
    assert result[0].strategy == "standard"
    assert result[0].successful == 2
    assert result[0].failed == 0
    assert result[0].total == 2
    assert result[0].success_rate == 100.0
    assert result[0].average_score == 85.0


def test_tracks_success_and_failure_together():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix add",
            strategy="standard",
            score=90.0,
        ),
        collector.repair_failure(
            "fix parser",
            strategy="standard",
            score=0.0,
        ),
    ]

    result = SuccessfulStrategyTracker().summarize(signals)

    assert result[0].successful == 1
    assert result[0].failed == 1
    assert result[0].total == 2
    assert result[0].success_rate == 50.0
    assert result[0].average_score == 45.0


def test_strategy_names_are_normalized():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix",
            strategy="  PROPERTY  ",
            score=90.0,
        ),
    ]

    result = SuccessfulStrategyTracker().summarize(signals)

    assert result[0].strategy == "property"


def test_empty_strategy_is_ignored():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix",
            strategy="",
            score=90.0,
        ),
    ]

    assert SuccessfulStrategyTracker().summarize(signals) == ()


def test_retries_and_rollbacks_are_not_standalone_outcomes():
    collector = LearningSignalCollector()

    signals = [
        collector.retry(
            "fix",
            strategy="mutation",
        ),
        collector.rollback(
            "fix",
            strategy="mutation",
        ),
    ]

    assert SuccessfulStrategyTracker().summarize(signals) == ()


def test_multiple_strategies_are_sorted_alphabetically_in_summary():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix",
            strategy="property",
            score=90.0,
        ),
        collector.repair_success(
            "fix",
            strategy="standard",
            score=80.0,
        ),
        collector.repair_success(
            "fix",
            strategy="mutation",
            score=95.0,
        ),
    ]

    result = SuccessfulStrategyTracker().summarize(signals)

    assert [item.strategy for item in result] == [
        "mutation",
        "property",
        "standard",
    ]


def test_rank_orders_by_success_rate_then_score():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "a",
            strategy="standard",
            score=95.0,
        ),
        collector.repair_failure(
            "b",
            strategy="standard",
            score=0.0,
        ),
        collector.repair_success(
            "c",
            strategy="property",
            score=80.0,
        ),
    ]

    result = SuccessfulStrategyTracker().rank(signals)

    assert result[0].strategy == "property"
    assert result[0].success_rate == 100.0
    assert result[1].strategy == "standard"


def test_best_returns_highest_ranked_strategy():
    collector = LearningSignalCollector()

    signals = [
        collector.verification_success(
            "verify",
            strategy="mutation",
            score=90.0,
        ),
        collector.verification_success(
            "verify",
            strategy="standard",
            score=70.0,
        ),
    ]

    best = SuccessfulStrategyTracker().best(signals)

    assert best is not None
    assert best.strategy == "mutation"


def test_best_returns_none_when_no_strategy_exists():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix",
            strategy="",
        ),
    ]

    assert SuccessfulStrategyTracker().best(signals) is None


def test_tracker_is_deterministic():
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
        ),
    ]

    tracker = SuccessfulStrategyTracker()

    first = tracker.rank(signals)
    second = tracker.rank(signals)

    assert first == second
