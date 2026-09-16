import pytest

from experience.effectiveness_policy import (
    EffectivenessAwarePolicy,
)
from experience.learning_effectiveness_aggregate import (
    LearningEffectivenessAggregate,
)
from experience.learning_policy import (
    LearningPolicyDecision,
)


def learning_allowed(
    strategy="property",
    confidence=80.0,
):
    return LearningPolicyDecision(
        allowed=True,
        strategy=strategy,
        confidence=confidence,
        reason="historical evidence is sufficient",
    )


def learning_rejected():
    return LearningPolicyDecision(
        allowed=False,
        strategy="property",
        confidence=50.0,
        reason="insufficient historical observations",
    )


def effectiveness(
    *,
    total=5,
    improved=4,
    regression=0,
    neutral=1,
    improvement_rate=80.0,
    regression_rate=0.0,
    average_improvement=10.0,
    average_confidence=30.0,
):
    return LearningEffectivenessAggregate(
        total_observations=total,
        improved_count=improved,
        regression_count=regression,
        neutral_count=neutral,
        improvement_rate=improvement_rate,
        regression_rate=regression_rate,
        average_improvement=average_improvement,
        average_confidence=average_confidence,
        consistently_improving=(
            improvement_rate >= 70.0
            and regression_rate < 20.0
            and average_improvement > 0.0
            and total >= 3
        ),
    )


def test_effective_strategy_is_allowed():
    result = EffectivenessAwarePolicy().decide(
        learning_decision=learning_allowed(),
        effectiveness=effectiveness(),
    )

    assert result.allowed is True
    assert result.strategy == "property"
    assert result.confidence == pytest.approx(55.0)


def test_base_learning_rejection_stops_learning():
    result = EffectivenessAwarePolicy().decide(
        learning_decision=learning_rejected(),
        effectiveness=effectiveness(),
    )

    assert result.allowed is False
    assert result.strategy == "property"
    assert "base learning policy rejected" in result.reason


def test_insufficient_effectiveness_history_is_rejected():
    result = EffectivenessAwarePolicy().decide(
        learning_decision=learning_allowed(),
        effectiveness=effectiveness(total=2),
    )

    assert result.allowed is False
    assert result.reason == (
        "insufficient effectiveness observations"
    )


def test_low_improvement_rate_is_rejected():
    result = EffectivenessAwarePolicy().decide(
        learning_decision=learning_allowed(),
        effectiveness=effectiveness(
            improvement_rate=60.0,
        ),
    )

    assert result.allowed is False
    assert result.reason == (
        "historical improvement rate is below "
        "effectiveness threshold"
    )


def test_high_regression_rate_is_rejected():
    result = EffectivenessAwarePolicy().decide(
        learning_decision=learning_allowed(),
        effectiveness=effectiveness(
            improvement_rate=80.0,
            regression_rate=20.0,
        ),
    )

    assert result.allowed is False
    assert result.reason == (
        "historical regression rate is above "
        "effectiveness threshold"
    )


def test_non_positive_average_improvement_is_rejected():
    result = EffectivenessAwarePolicy().decide(
        learning_decision=learning_allowed(),
        effectiveness=effectiveness(
            average_improvement=0.0,
        ),
    )

    assert result.allowed is False
    assert result.reason == (
        "average historical improvement is not positive"
    )


def test_threshold_boundary_for_improvement_is_allowed():
    result = EffectivenessAwarePolicy(
        min_improvement_rate=70.0,
    ).decide(
        learning_decision=learning_allowed(),
        effectiveness=effectiveness(
            improvement_rate=70.0,
            regression_rate=0.0,
            average_improvement=1.0,
        ),
    )

    assert result.allowed is True


def test_threshold_boundary_for_regression_is_rejected():
    result = EffectivenessAwarePolicy(
        max_regression_rate=20.0,
    ).decide(
        learning_decision=learning_allowed(),
        effectiveness=effectiveness(
            improvement_rate=80.0,
            regression_rate=20.0,
            average_improvement=10.0,
        ),
    )

    assert result.allowed is False


def test_custom_thresholds_are_respected():
    policy = EffectivenessAwarePolicy(
        min_improvement_rate=80.0,
        max_regression_rate=10.0,
        min_average_improvement=5.1,
        min_observations=5,
    )

    result = policy.decide(
        learning_decision=learning_allowed(),
        effectiveness=effectiveness(
            total=5,
            improvement_rate=80.0,
            regression_rate=10.0 - 0.1,
            average_improvement=5.1,
        ),
    )

    assert result.allowed is True


def test_confidence_is_capped():
    result = EffectivenessAwarePolicy().decide(
        learning_decision=learning_allowed(
            confidence=100.0,
        ),
        effectiveness=effectiveness(
            average_confidence=100.0,
        ),
    )

    assert result.confidence == 100.0


def test_custom_strategy_is_preserved():
    result = EffectivenessAwarePolicy().decide(
        learning_decision=learning_allowed(
            strategy="mutation",
        ),
        effectiveness=effectiveness(),
    )

    assert result.strategy == "mutation"


def test_invalid_improvement_threshold_is_rejected():
    with pytest.raises(
        ValueError,
        match="min_improvement_rate must be between 0 and 100",
    ):
        EffectivenessAwarePolicy(
            min_improvement_rate=101.0,
        )


def test_invalid_regression_threshold_is_rejected():
    with pytest.raises(
        ValueError,
        match="max_regression_rate must be between 0 and 100",
    ):
        EffectivenessAwarePolicy(
            max_regression_rate=-1.0,
        )


def test_invalid_average_improvement_threshold_is_rejected():
    with pytest.raises(
        ValueError,
        match="min_average_improvement must be at least 0",
    ):
        EffectivenessAwarePolicy(
            min_average_improvement=-1.0,
        )


def test_invalid_observation_threshold_is_rejected():
    with pytest.raises(
        ValueError,
        match="min_observations must be at least 1",
    ):
        EffectivenessAwarePolicy(
            min_observations=0,
        )


def test_policy_is_deterministic():
    policy = EffectivenessAwarePolicy()

    learning = learning_allowed()
    effectiveness_result = effectiveness()

    first = policy.decide(
        learning_decision=learning,
        effectiveness=effectiveness_result,
    )
    second = policy.decide(
        learning_decision=learning,
        effectiveness=effectiveness_result,
    )

    assert first == second
