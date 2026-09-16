from experience.adaptive_strategy import AdaptiveStrategyScore
from experience.effectiveness_policy import (
    EffectivenessAwarePolicy,
)
from experience.effectiveness_ranker import (
    EffectivenessAwareRanker,
)
from experience.effectiveness_router import (
    EffectivenessAwareRouter,
)
from experience.learning_effectiveness_aggregate import (
    LearningEffectivenessAggregate,
)
from experience.learning_signal import LearningSignalCollector


def effectiveness(
    *,
    total=5,
    improvement_rate=80.0,
    regression_rate=0.0,
    average_improvement=20.0,
):
    return LearningEffectivenessAggregate(
        total_observations=total,
        improved_count=4,
        regression_count=0,
        neutral_count=1,
        improvement_rate=improvement_rate,
        regression_rate=regression_rate,
        average_improvement=average_improvement,
        average_confidence=40.0,
        consistently_improving=(
            total >= 3
            and improvement_rate >= 70.0
            and regression_rate < 20.0
            and average_improvement > 0.0
        ),
    )


def test_effective_history_selects_strategy():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=95.0,
        )
        for index in range(5)
    ]

    result = EffectivenessAwareRouter().route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 95.0},
        effectiveness_by_strategy={
            "property": effectiveness(
                improvement_rate=100.0,
                average_improvement=30.0,
            ),
        },
    )

    assert result.strategy == "property"
    assert result.learned is True
    assert result.confidence > 0.0


def test_missing_effectiveness_history_uses_default():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=95.0,
        )
        for index in range(5)
    ]

    result = EffectivenessAwareRouter().route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 95.0},
    )

    assert result.strategy == "standard"
    assert result.learned is False


def test_insufficient_effectiveness_history_uses_default():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=95.0,
        )
        for index in range(5)
    ]

    result = EffectivenessAwareRouter().route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 95.0},
        effectiveness_by_strategy={
            "property": effectiveness(total=2),
        },
    )

    assert result.strategy == "standard"
    assert result.learned is False


def test_regression_heavy_history_uses_default():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=95.0,
        )
        for index in range(5)
    ]

    result = EffectivenessAwareRouter().route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 95.0},
        effectiveness_by_strategy={
            "property": effectiveness(
                improvement_rate=40.0,
                regression_rate=40.0,
            ),
        },
    )

    assert result.strategy == "standard"
    assert result.learned is False


def test_no_signals_uses_default():
    result = EffectivenessAwareRouter().route(
        default_strategy="standard",
        signals=[],
    )

    assert result.strategy == "standard"
    assert result.learned is False
    assert result.confidence == 0.0


def test_default_strategy_is_trimmed():
    result = EffectivenessAwareRouter().route(
        default_strategy="  standard  ",
        signals=[],
    )

    assert result.strategy == "standard"


def test_empty_default_strategy_is_rejected():
    try:
        EffectivenessAwareRouter().route(
            default_strategy="   ",
            signals=[],
        )
    except ValueError as exc:
        assert str(exc) == "default_strategy must not be empty"
    else:
        raise AssertionError("expected ValueError")


def test_custom_effectiveness_policy_is_respected():
    class RejectPolicy(EffectivenessAwarePolicy):
        def decide(
            self,
            *,
            learning_decision,
            effectiveness,
        ):
            from experience.effectiveness_policy import (
                EffectivenessPolicyDecision,
            )

            return EffectivenessPolicyDecision(
                allowed=False,
                strategy=learning_decision.strategy,
                confidence=0.0,
                reason="forced rejection",
            )

    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=95.0,
        )
        for index in range(5)
    ]

    result = EffectivenessAwareRouter(
        effectiveness_policy=RejectPolicy(),
    ).route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 95.0},
        effectiveness_by_strategy={
            "property": effectiveness(
                improvement_rate=100.0,
            ),
        },
    )

    assert result.strategy == "standard"
    assert result.learned is False
    assert "forced rejection" in result.reason


def test_custom_rankers_are_respected():
    class FixedAdaptiveRanker:
        def rank(self, signals, utility_by_strategy=None):
            return (
                AdaptiveStrategyScore(
                    strategy="property",
                    score=90.0,
                    success_rate=100.0,
                    average_outcome_score=90.0,
                    utility_score=90.0,
                    failure_penalty=0.0,
                    total_outcomes=5,
                ),
            )

    class FixedEffectivenessRanker:
        def rank(
            self,
            strategies,
            effectiveness_by_strategy=None,
        ):
            return (
                __import__(
                    "experience.effectiveness_ranker",
                    fromlist=["EffectivenessAwareStrategyScore"],
                ).EffectivenessAwareStrategyScore(
                    strategy="property",
                    score=90.0,
                    adaptive_score=90.0,
                    effectiveness_score=90.0,
                    improvement_rate=100.0,
                    regression_rate=0.0,
                    total_observations=5,
                ),
            )

    collector = LearningSignalCollector()

    result = EffectivenessAwareRouter(
        adaptive_ranker=FixedAdaptiveRanker(),
        effectiveness_ranker=FixedEffectivenessRanker(),
    ).route(
        default_strategy="standard",
        signals=[
            collector.repair_success(
                "fix",
                strategy="standard",
            )
        ],
        effectiveness_by_strategy={
            "property": effectiveness(
                improvement_rate=100.0,
            ),
        },
    )

    assert result.strategy == "property"
    assert result.learned is True


def test_router_is_deterministic():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=95.0,
        )
        for index in range(5)
    ]

    kwargs = {
        "default_strategy": "standard",
        "signals": signals,
        "utility_by_strategy": {
            "property": 95.0,
        },
        "effectiveness_by_strategy": {
            "property": effectiveness(
                improvement_rate=100.0,
            ),
        },
    }

    router = EffectivenessAwareRouter()

    first = router.route(**kwargs)
    second = router.route(**kwargs)

    assert first == second
