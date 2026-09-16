import pytest
from experience.failure_tracker import FailedStrategyTracker
from experience.learning_signal import LearningSignalCollector


def test_summarizes_repair_failures():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_failure(
            "fix parser",
            strategy="standard",
        ),
        collector.repair_failure(
            "fix parser",
            strategy="standard",
        ),
    ]

    result = FailedStrategyTracker().summarize(signals)

    assert len(result) == 1
    assert result[0].strategy == "standard"
    assert result[0].failures == 2
    assert result[0].retries == 0
    assert result[0].rollbacks == 0
    assert result[0].total_negative_events == 2
    assert result[0].failure_rate == 100.0


def test_verification_failures_are_counted():
    collector = LearningSignalCollector()

    signals = [
        collector.verification_failure(
            "verify fix",
            strategy="property",
        ),
    ]

    result = FailedStrategyTracker().summarize(signals)

    assert result[0].failures == 1
    assert result[0].failure_rate == 100.0


def test_retries_are_tracked_separately():
    collector = LearningSignalCollector()

    signals = [
        collector.retry(
            "repair",
            strategy="mutation",
        ),
        collector.retry(
            "repair",
            strategy="mutation",
        ),
    ]

    result = FailedStrategyTracker().summarize(signals)

    assert result[0].failures == 0
    assert result[0].retries == 2
    assert result[0].rollbacks == 0
    assert result[0].retry_rate == 100.0


def test_rollbacks_are_tracked_separately():
    collector = LearningSignalCollector()

    signals = [
        collector.rollback(
            "repair",
            strategy="multifile",
        ),
        collector.rollback(
            "repair",
            strategy="multifile",
        ),
    ]

    result = FailedStrategyTracker().summarize(signals)

    assert result[0].failures == 0
    assert result[0].retries == 0
    assert result[0].rollbacks == 2
    assert result[0].rollback_rate == 100.0


def test_negative_event_rates_are_calculated():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_failure(
            "a",
            strategy="standard",
        ),
        collector.retry(
            "a",
            strategy="standard",
        ),
        collector.rollback(
            "a",
            strategy="standard",
        ),
    ]

    result = FailedStrategyTracker().summarize(signals)

    assert result[0].total_negative_events == 3
    assert result[0].failure_rate == pytest.approx(100.0 / 3.0)
    assert result[0].retry_rate == pytest.approx(100.0 / 3.0)
    assert result[0].rollback_rate == pytest.approx(100.0 / 3.0)


def test_success_signals_are_not_negative_events():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix",
            strategy="property",
        ),
        collector.verification_success(
            "verify",
            strategy="property",
        ),
    ]

    assert FailedStrategyTracker().summarize(signals) == ()


def test_empty_strategy_is_ignored():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_failure(
            "fix",
            strategy="",
        ),
        collector.retry(
            "fix",
            strategy="",
        ),
    ]

    assert FailedStrategyTracker().summarize(signals) == ()


def test_multiple_strategies_are_separated():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_failure(
            "a",
            strategy="standard",
        ),
        collector.retry(
            "b",
            strategy="property",
        ),
    ]

    result = FailedStrategyTracker().summarize(signals)

    assert [item.strategy for item in result] == [
        "property",
        "standard",
    ]


def test_rank_prioritizes_rollbacks():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_failure(
            "a",
            strategy="standard",
        ),
        collector.rollback(
            "b",
            strategy="property",
        ),
    ]

    result = FailedStrategyTracker().rank(signals)

    assert result[0].strategy == "property"


def test_worst_returns_highest_negative_profile():
    collector = LearningSignalCollector()

    signals = [
        collector.retry(
            "a",
            strategy="standard",
        ),
        collector.rollback(
            "b",
            strategy="mutation",
        ),
    ]

    worst = FailedStrategyTracker().worst(signals)

    assert worst is not None
    assert worst.strategy == "mutation"


def test_worst_returns_none_without_negative_events():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix",
            strategy="standard",
        ),
    ]

    assert FailedStrategyTracker().worst(signals) is None


def test_tracker_is_deterministic():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_failure(
            "a",
            strategy="standard",
        ),
        collector.retry(
            "b",
            strategy="standard",
        ),
        collector.rollback(
            "c",
            strategy="mutation",
        ),
    ]

    tracker = FailedStrategyTracker()

    first = tracker.rank(signals)
    second = tracker.rank(signals)

    assert first == second
