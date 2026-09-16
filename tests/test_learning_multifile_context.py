from agents.learning_multifile_context import (
    LearningMultiFileContextBuilder,
)
from experience.historical_learning_injection import (
    HistoricalLearningInjection,
)
from experience.learning_signal import (
    LearningSignal,
    LearningSignalType,
)


def make_signal(
    *,
    strategy="multifile",
    score=90.0,
):
    return LearningSignal(
        signal_type=LearningSignalType.REPAIR_SUCCESS,
        task="repair project",
        strategy=strategy,
        attempts=1,
        score=score,
        metadata="",
    )


def make_injection(
    signals=(),
    utility=None,
):
    return HistoricalLearningInjection(
        signals=tuple(signals),
        utility_by_strategy=utility or {},
        retrieved=len(signals),
    )


def test_builds_multifile_context():
    injection = make_injection(
        [make_signal()],
        {"multifile": 90.0},
    )

    result = LearningMultiFileContextBuilder().build(
        task="repair project",
        injection=injection,
    )

    assert result.task == "repair project"
    assert result.signals == injection.signals
    assert result.strategies == ("multifile",)
    assert "multifile" in result.guidance[0]


def test_multiple_strategies_are_sorted():
    injection = make_injection(
        [
            make_signal(strategy="standard"),
            make_signal(strategy="multifile"),
            make_signal(strategy="mutation"),
        ],
        {
            "standard": 80.0,
            "multifile": 90.0,
            "mutation": 95.0,
        },
    )

    result = LearningMultiFileContextBuilder().build(
        task="repair",
        injection=injection,
    )

    assert result.strategies == (
        "multifile",
        "mutation",
        "standard",
    )


def test_duplicate_strategies_are_removed():
    injection = make_injection(
        [
            make_signal(strategy="multifile"),
            make_signal(strategy="multifile"),
        ],
        {"multifile": 90.0},
    )

    result = LearningMultiFileContextBuilder().build(
        task="repair",
        injection=injection,
    )

    assert result.strategies == ("multifile",)


def test_strategy_names_are_normalized():
    injection = make_injection(
        [make_signal(strategy="  MULTIFILE  ")],
        {"multifile": 90.0},
    )

    result = LearningMultiFileContextBuilder().build(
        task="repair",
        injection=injection,
    )

    assert result.strategies == ("multifile",)


def test_empty_history_is_safe():
    result = LearningMultiFileContextBuilder().build(
        task="repair",
        injection=make_injection(),
    )

    assert result.signals == ()
    assert result.strategies == ()
    assert (
        "No historical multi-file repair experience is available"
        in result.guidance
    )


def test_repository_state_priority_is_explicit():
    result = LearningMultiFileContextBuilder().build(
        task="repair",
        injection=make_injection(),
    )

    assert any(
        "Current repository state" in item
        for item in result.guidance
    )


def test_validation_priority_is_explicit():
    result = LearningMultiFileContextBuilder().build(
        task="repair",
        injection=make_injection(),
    )

    assert any(
        "patch validation" in item
        for item in result.guidance
    )


def test_rollback_safeguard_is_explicit():
    result = LearningMultiFileContextBuilder().build(
        task="repair",
        injection=make_injection(),
    )

    assert any(
        "rollback safeguards remain mandatory" in item
        for item in result.guidance
    )


def test_empty_task_is_rejected():
    try:
        LearningMultiFileContextBuilder().build(
            task="   ",
            injection=make_injection(),
        )
    except ValueError as exc:
        assert str(exc) == "task must not be empty"
    else:
        raise AssertionError("expected ValueError")


def test_context_is_deterministic():
    injection = make_injection(
        [
            make_signal(strategy="multifile"),
            make_signal(strategy="mutation"),
        ],
        {
            "multifile": 90.0,
            "mutation": 95.0,
        },
    )

    builder = LearningMultiFileContextBuilder()

    first = builder.build(
        task="repair",
        injection=injection,
    )
    second = builder.build(
        task="repair",
        injection=injection,
    )

    assert first == second
