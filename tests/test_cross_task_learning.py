import pytest

from experience.cross_task_learning import CrossTaskLearning
from experience.learning_signal import LearningSignalCollector


def test_builds_cross_task_profile():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix parser A",
            strategy="property",
            score=90.0,
        ),
        collector.repair_success(
            "fix parser B",
            strategy="property",
            score=80.0,
        ),
    ]

    result = CrossTaskLearning().build(
        task_family="parser",
        signals=signals,
    )

    assert result.task_family == "parser"
    assert result.signals == tuple(signals)
    assert result.strategies == ("property",)
    assert result.average_score == 85.0
    assert result.successful_count == 2
    assert result.failed_count == 0


def test_failed_signals_are_counted():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_failure(
            "parser",
            strategy="standard",
        ),
        collector.verification_failure(
            "parser",
            strategy="standard",
        ),
    ]

    result = CrossTaskLearning().build(
        task_family="parser",
        signals=signals,
    )

    assert result.failed_count == 2
    assert result.successful_count == 0
    assert result.average_score == 0.0


def test_mixed_outcomes_are_supported():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "a",
            strategy="property",
            score=90.0,
        ),
        collector.repair_failure(
            "b",
            strategy="property",
            score=20.0,
        ),
    ]

    result = CrossTaskLearning().build(
        task_family="parser",
        signals=signals,
    )

    assert result.successful_count == 1
    assert result.failed_count == 1
    assert result.average_score == 55.0


def test_multiple_strategies_are_sorted_and_unique():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "a",
            strategy="standard",
            score=80.0,
        ),
        collector.repair_success(
            "b",
            strategy="property",
            score=90.0,
        ),
        collector.repair_success(
            "c",
            strategy="standard",
            score=85.0,
        ),
    ]

    result = CrossTaskLearning().build(
        task_family="parser",
        signals=signals,
    )

    assert result.strategies == (
        "property",
        "standard",
    )


def test_task_family_is_trimmed():
    result = CrossTaskLearning().build(
        task_family="  parser  ",
        signals=[],
    )

    assert result.task_family == "parser"


def test_empty_task_family_is_rejected():
    with pytest.raises(
        ValueError,
        match="task_family must not be empty",
    ):
        CrossTaskLearning().build(
            task_family="   ",
            signals=[],
        )


def test_empty_signal_set_is_safe():
    result = CrossTaskLearning().build(
        task_family="parser",
        signals=[],
    )

    assert result.signals == ()
    assert result.strategies == ()
    assert result.average_score == 0.0
    assert result.successful_count == 0
    assert result.failed_count == 0


def test_merge_combines_profiles_in_same_family():
    collector = LearningSignalCollector()

    first = CrossTaskLearning().build(
        task_family="parser",
        signals=[
            collector.repair_success(
                "a",
                strategy="property",
                score=90.0,
            ),
        ],
    )

    second = CrossTaskLearning().build(
        task_family="parser",
        signals=[
            collector.repair_failure(
                "b",
                strategy="standard",
                score=0.0,
            ),
        ],
    )

    result = CrossTaskLearning().merge([first, second])

    assert len(result) == 1
    assert result[0].task_family == "parser"
    assert len(result[0].signals) == 2
    assert result[0].successful_count == 1
    assert result[0].failed_count == 1


def test_merge_keeps_different_families_separate():
    collector = LearningSignalCollector()

    parser = CrossTaskLearning().build(
        task_family="parser",
        signals=[
            collector.repair_success(
                "parser",
                strategy="property",
                score=90.0,
            ),
        ],
    )

    database = CrossTaskLearning().build(
        task_family="database",
        signals=[
            collector.repair_success(
                "database",
                strategy="standard",
                score=80.0,
            ),
        ],
    )

    result = CrossTaskLearning().merge(
        [parser, database]
    )

    assert [profile.task_family for profile in result] == [
        "database",
        "parser",
    ]
    assert result[0].signals[0].task == "database"
    assert result[1].signals[0].task == "parser"


def test_merge_ignores_empty_family_profiles():
    collector = LearningSignalCollector()

    valid = CrossTaskLearning().build(
        task_family="parser",
        signals=[
            collector.repair_success(
                "parser",
                strategy="property",
                score=90.0,
            ),
        ],
    )

    invalid_like = CrossTaskLearning().build(
        task_family="temporary",
        signals=[],
    )

    result = CrossTaskLearning().merge(
        [valid, invalid_like]
    )

    assert [profile.task_family for profile in result] == [
        "parser",
        "temporary",
    ]


def test_cross_task_profile_is_deterministic():
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

    learning = CrossTaskLearning()

    first = learning.build(
        task_family="parser",
        signals=signals,
    )
    second = learning.build(
        task_family="parser",
        signals=signals,
    )

    assert first == second
