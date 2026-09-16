from experience.learning_safety import LearningSafetyGuard
from experience.learning_signal import LearningSignalCollector


def test_empty_signals_are_safe_and_unusable():
    result = LearningSafetyGuard().filter(
        task_family="parser",
        signals=[],
        allow_cross_task=True,
    )

    assert result.allowed is False
    assert result.signals == ()
    assert result.reason == "no learning signals available"


def test_same_task_signals_are_allowed_without_cross_task_mode():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix parser",
            strategy="property",
            score=90.0,
        ),
    ]

    result = LearningSafetyGuard().filter(
        task_family=None,
        signals=signals,
        allow_cross_task=False,
    )

    assert result.allowed is True
    assert result.signals == tuple(signals)
    assert result.reason == "cross-task learning is disabled"


def test_cross_task_requires_task_family():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix parser",
            strategy="property",
            metadata="task_family=parser",
        ),
    ]

    result = LearningSafetyGuard().filter(
        task_family="",
        signals=signals,
        allow_cross_task=True,
    )

    assert result.allowed is False
    assert result.signals == ()
    assert "task family is required" in result.reason


def test_matching_task_family_is_allowed():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix parser",
            strategy="property",
            metadata="task_family=parser",
        ),
    ]

    result = LearningSafetyGuard().filter(
        task_family="parser",
        signals=signals,
        allow_cross_task=True,
    )

    assert result.allowed is True
    assert result.signals == tuple(signals)


def test_non_matching_task_family_is_rejected():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix database",
            strategy="standard",
            metadata="task_family=database",
        ),
    ]

    result = LearningSafetyGuard().filter(
        task_family="parser",
        signals=signals,
        allow_cross_task=True,
    )

    assert result.allowed is False
    assert result.signals == ()
    assert "no learning signals match" in result.reason


def test_mixed_families_are_filtered():
    collector = LearningSignalCollector()

    parser = collector.repair_success(
        "parser",
        strategy="property",
        metadata="task_family=parser",
    )
    database = collector.repair_success(
        "database",
        strategy="standard",
        metadata="task_family=database",
    )

    result = LearningSafetyGuard().filter(
        task_family="parser",
        signals=[parser, database],
        allow_cross_task=True,
    )

    assert result.allowed is True
    assert result.signals == (parser,)


def test_family_matching_is_exact():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "parser advanced",
            strategy="property",
            metadata="task_family=parser-advanced",
        ),
    ]

    result = LearningSafetyGuard().filter(
        task_family="parser",
        signals=signals,
        allow_cross_task=True,
    )

    assert result.allowed is False


def test_family_matching_ignores_metadata_key_case():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "parser",
            strategy="property",
            metadata="TASK_FAMILY=parser",
        ),
    ]

    result = LearningSafetyGuard().filter(
        task_family="parser",
        signals=signals,
        allow_cross_task=True,
    )

    assert result.allowed is True


def test_family_value_whitespace_is_normalized():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "parser",
            strategy="property",
            metadata="task_family= parser ",
        ),
    ]

    result = LearningSafetyGuard().filter(
        task_family="parser",
        signals=signals,
        allow_cross_task=True,
    )

    assert result.allowed is True


def test_signals_without_family_are_excluded():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "unscoped",
            strategy="property",
            metadata="strategy=property",
        ),
        collector.repair_success(
            "parser",
            strategy="property",
            metadata="task_family=parser",
        ),
    ]

    result = LearningSafetyGuard().filter(
        task_family="parser",
        signals=signals,
        allow_cross_task=True,
    )

    assert result.signals == (signals[1],)


def test_filtering_is_deterministic():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "a",
            strategy="property",
            metadata="task_family=parser",
        ),
        collector.repair_success(
            "b",
            strategy="standard",
            metadata="task_family=database",
        ),
    ]

    guard = LearningSafetyGuard()

    first = guard.filter(
        task_family="parser",
        signals=signals,
        allow_cross_task=True,
    )
    second = guard.filter(
        task_family="parser",
        signals=signals,
        allow_cross_task=True,
    )

    assert first == second


def test_nested_source_metadata_task_family_is_allowed():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "parser",
            strategy="property",
            metadata=(
                "strategy=property; attempts=1; score=90.00; "
                "source_metadata=task_family=parser"
            ),
        ),
    ]

    result = LearningSafetyGuard().filter(
        task_family="parser",
        signals=signals,
        allow_cross_task=True,
    )

    assert result.allowed is True
    assert result.signals == (signals[0],)


def test_nested_non_matching_source_metadata_is_rejected():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "database",
            strategy="standard",
            metadata=(
                "strategy=standard; attempts=1; score=80.00; "
                "source_metadata=task_family=database"
            ),
        ),
    ]

    result = LearningSafetyGuard().filter(
        task_family="parser",
        signals=signals,
        allow_cross_task=True,
    )

    assert result.allowed is False
    assert result.signals == ()
