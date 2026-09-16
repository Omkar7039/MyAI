from agents.learning_debug_context import (
    LearningDebugContextBuilder,
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
    strategy="property",
    score=90.0,
):
    return LearningSignal(
        signal_type=LearningSignalType.REPAIR_SUCCESS,
        task="fix bug",
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


def test_builds_debug_context_from_history():
    injection = make_injection(
        [make_signal()],
        {"property": 90.0},
    )

    result = LearningDebugContextBuilder().build(
        task="debug add",
        injection=injection,
    )

    assert result.task == "debug add"
    assert len(result.signals) == 1
    assert result.strategies == ("property",)
    assert "property" in result.guidance[0]


def test_multiple_strategies_are_sorted():
    injection = make_injection(
        [
            make_signal(strategy="standard"),
            make_signal(strategy="property"),
            make_signal(strategy="mutation"),
        ],
        {
            "standard": 80.0,
            "property": 90.0,
            "mutation": 95.0,
        },
    )

    result = LearningDebugContextBuilder().build(
        task="debug",
        injection=injection,
    )

    assert result.strategies == (
        "mutation",
        "property",
        "standard",
    )


def test_duplicate_strategies_are_removed():
    injection = make_injection(
        [
            make_signal(strategy="property"),
            make_signal(strategy="property"),
        ],
        {"property": 90.0},
    )

    result = LearningDebugContextBuilder().build(
        task="debug",
        injection=injection,
    )

    assert result.strategies == ("property",)


def test_strategy_names_are_normalized():
    injection = make_injection(
        [make_signal(strategy="  PROPERTY  ")],
        {"property": 90.0},
    )

    result = LearningDebugContextBuilder().build(
        task="debug",
        injection=injection,
    )

    assert result.strategies == ("property",)


def test_empty_history_is_safe():
    result = LearningDebugContextBuilder().build(
        task="debug",
        injection=make_injection(),
    )

    assert result.signals == ()
    assert result.strategies == ()
    assert (
        "No historical debugging experience is available"
        in result.guidance
    )


def test_current_evidence_priority_is_explicit():
    result = LearningDebugContextBuilder().build(
        task="debug",
        injection=make_injection(),
    )

    assert any(
        "Current source, tests, and investigation evidence"
        in item
        for item in result.guidance
    )


def test_historical_learning_is_explicitly_advisory():
    result = LearningDebugContextBuilder().build(
        task="debug",
        injection=make_injection(),
    )

    assert any(
        "advisory context" in item
        for item in result.guidance
    )


def test_empty_task_is_rejected():
    try:
        LearningDebugContextBuilder().build(
            task="   ",
            injection=make_injection(),
        )
    except ValueError as exc:
        assert str(exc) == "task must not be empty"
    else:
        raise AssertionError("expected ValueError")


def test_signal_identity_is_preserved():
    signal = make_signal()

    result = LearningDebugContextBuilder().build(
        task="debug",
        injection=make_injection(
            [signal],
            {"property": 90.0},
        ),
    )

    assert result.signals == (signal,)


def test_context_is_deterministic():
    injection = make_injection(
        [
            make_signal(strategy="property"),
            make_signal(strategy="mutation"),
        ],
        {
            "property": 90.0,
            "mutation": 95.0,
        },
    )

    builder = LearningDebugContextBuilder()

    first = builder.build(
        task="debug",
        injection=injection,
    )
    second = builder.build(
        task="debug",
        injection=injection,
    )

    assert first == second
