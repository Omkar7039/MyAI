from experience.historical_learning_injection import (
    HistoricalLearningInjection,
)
from experience.learning_signal import (
    LearningSignal,
    LearningSignalType,
)
from verification.learning_verification_context import (
    LearningVerificationContextBuilder,
)


def make_signal(
    *,
    strategy="property",
    score=90.0,
):
    return LearningSignal(
        signal_type=LearningSignalType.VERIFICATION_SUCCESS,
        task="verify repair",
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


def test_builds_verification_context():
    injection = make_injection(
        [make_signal()],
        {"property": 90.0},
    )

    result = LearningVerificationContextBuilder().build(
        task="verify add",
        injection=injection,
    )

    assert result.task == "verify add"
    assert result.signals == injection.signals
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

    result = LearningVerificationContextBuilder().build(
        task="verify",
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

    result = LearningVerificationContextBuilder().build(
        task="verify",
        injection=injection,
    )

    assert result.strategies == ("property",)


def test_strategy_names_are_normalized():
    injection = make_injection(
        [make_signal(strategy="  PROPERTY  ")],
        {"property": 90.0},
    )

    result = LearningVerificationContextBuilder().build(
        task="verify",
        injection=injection,
    )

    assert result.strategies == ("property",)


def test_empty_history_is_safe():
    result = LearningVerificationContextBuilder().build(
        task="verify",
        injection=make_injection(),
    )

    assert result.signals == ()
    assert result.strategies == ()
    assert (
        "No historical verification experience is available"
        in result.guidance
    )


def test_current_test_priority_is_explicit():
    result = LearningVerificationContextBuilder().build(
        task="verify",
        injection=make_injection(),
    )

    assert any(
        "Current tests and verification evidence take priority"
        in item
        for item in result.guidance
    )


def test_mutation_property_authority_is_explicit():
    result = LearningVerificationContextBuilder().build(
        task="verify",
        injection=make_injection(),
    )

    assert any(
        "Mutation and property verification remain authoritative"
        in item
        for item in result.guidance
    )


def test_advisory_nature_is_explicit():
    result = LearningVerificationContextBuilder().build(
        task="verify",
        injection=make_injection(),
    )

    assert any(
        "advisory verification guidance" in item
        for item in result.guidance
    )


def test_empty_task_is_rejected():
    try:
        LearningVerificationContextBuilder().build(
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
            make_signal(strategy="property"),
            make_signal(strategy="mutation"),
        ],
        {
            "property": 90.0,
            "mutation": 95.0,
        },
    )

    builder = LearningVerificationContextBuilder()

    first = builder.build(
        task="verify",
        injection=injection,
    )
    second = builder.build(
        task="verify",
        injection=injection,
    )

    assert first == second
