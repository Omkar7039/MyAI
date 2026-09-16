import pytest

from experience.adaptive_strategy import AdaptiveStrategyScore
from experience.effectiveness_ranker import (
    EffectivenessAwareRanker,
)
from experience.learning_effectiveness_aggregate import (
    LearningEffectivenessAggregate,
)


def adaptive(
    strategy,
    score,
):
    return AdaptiveStrategyScore(
        strategy=strategy,
        score=score,
        success_rate=80.0,
        average_outcome_score=80.0,
        utility_score=70.0,
        failure_penalty=0.0,
        total_outcomes=5,
    )


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


def test_combines_adaptive_and_effectiveness():
    result = EffectivenessAwareRanker().rank(
        [adaptive("property", 80.0)],
        {"property": effectiveness()},
    )

    assert len(result) == 1
    assert result[0].strategy == "property"
    assert result[0].adaptive_score == 80.0
    assert result[0].improvement_rate == 80.0
    assert result[0].regression_rate == 0.0
    assert result[0].total_observations == 5
    assert result[0].effectiveness_score == pytest.approx(68.0)
    assert result[0].score == pytest.approx(75.2)


def test_missing_effectiveness_has_zero_effectiveness_component():
    result = EffectivenessAwareRanker().rank(
        [adaptive("standard", 80.0)],
    )

    assert result[0].effectiveness_score == 0.0
    assert result[0].total_observations == 0
    assert result[0].score == pytest.approx(48.0)


def test_high_effectiveness_can_change_ranking():
    result = EffectivenessAwareRanker().rank(
        [
            adaptive("standard", 90.0),
            adaptive("property", 70.0),
        ],
        {
            "property": effectiveness(
                improvement_rate=100.0,
                average_improvement=40.0,
            ),
            "standard": effectiveness(
                improvement_rate=20.0,
                regression_rate=40.0,
                average_improvement=2.0,
            ),
        },
    )

    assert result[0].strategy == "property"


def test_high_regression_reduces_effectiveness_score():
    normal = EffectivenessAwareRanker().rank(
        [adaptive("property", 80.0)],
        {
            "property": effectiveness(
                improvement_rate=80.0,
                regression_rate=0.0,
            ),
        },
    )[0]

    regressed = EffectivenessAwareRanker().rank(
        [adaptive("property", 80.0)],
        {
            "property": effectiveness(
                improvement_rate=80.0,
                regression_rate=20.0,
            ),
        },
    )[0]

    assert regressed.effectiveness_score < (
        normal.effectiveness_score
    )


def test_average_improvement_contributes_to_score():
    low = EffectivenessAwareRanker().rank(
        [adaptive("property", 80.0)],
        {
            "property": effectiveness(
                improvement_rate=80.0,
                average_improvement=5.0,
            ),
        },
    )[0]

    high = EffectivenessAwareRanker().rank(
        [adaptive("property", 80.0)],
        {
            "property": effectiveness(
                improvement_rate=80.0,
                average_improvement=40.0,
            ),
        },
    )[0]

    assert high.effectiveness_score > low.effectiveness_score


def test_effectiveness_average_improvement_is_capped():
    result = EffectivenessAwareRanker().rank(
        [adaptive("property", 80.0)],
        {
            "property": effectiveness(
                improvement_rate=100.0,
                average_improvement=500.0,
            ),
        },
    )[0]

    assert result.effectiveness_score == 100.0


def test_strategy_names_are_normalized():
    result = EffectivenessAwareRanker().rank(
        [adaptive("  PROPERTY  ", 80.0)],
        {
            "property": effectiveness(),
        },
    )

    assert result[0].strategy == "property"


def test_empty_strategy_list_returns_empty():
    assert EffectivenessAwareRanker().rank([]) == ()


def test_best_returns_top_strategy():
    result = EffectivenessAwareRanker().best(
        [
            adaptive("standard", 70.0),
            adaptive("property", 90.0),
        ],
        {
            "standard": effectiveness(
                improvement_rate=50.0,
            ),
            "property": effectiveness(
                improvement_rate=90.0,
                average_improvement=30.0,
            ),
        },
    )

    assert result is not None
    assert result.strategy == "property"


def test_best_returns_none_when_empty():
    assert EffectivenessAwareRanker().best([]) is None


def test_input_order_does_not_change_rank():
    strategies = [
        adaptive("standard", 80.0),
        adaptive("property", 80.0),
    ]

    effectiveness_map = {
        "standard": effectiveness(
            improvement_rate=70.0,
        ),
        "property": effectiveness(
            improvement_rate=90.0,
        ),
    }

    ranker = EffectivenessAwareRanker()

    first = ranker.rank(
        strategies,
        effectiveness_map,
    )
    second = ranker.rank(
        list(reversed(strategies)),
        effectiveness_map,
    )

    assert first == second


def test_ranking_is_deterministic():
    strategies = [adaptive("property", 85.0)]
    effectiveness_map = {
        "property": effectiveness(),
    }

    ranker = EffectivenessAwareRanker()

    first = ranker.rank(strategies, effectiveness_map)
    second = ranker.rank(strategies, effectiveness_map)

    assert first == second
