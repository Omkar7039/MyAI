from __future__ import annotations

from dataclasses import dataclass

from experience.learning_effectiveness import (
    LearningEffectivenessEvaluator,
)


@dataclass(frozen=True)
class LearningEffectivenessAggregate:
    total_observations: int
    improved_count: int
    regression_count: int
    neutral_count: int
    improvement_rate: float
    regression_rate: float
    average_improvement: float
    average_confidence: float
    consistently_improving: bool


class LearningEffectivenessAggregator:
    """
    Aggregate repeated learned-vs-baseline evaluations.

    An improvement is considered consistent when:
      - at least 3 observations exist
      - improvement rate >= 70%
      - regression rate < 20%
      - average improvement > 0
    """

    def __init__(
        self,
        evaluator: LearningEffectivenessEvaluator | None = None,
    ):
        self.evaluator = evaluator or LearningEffectivenessEvaluator()

    def aggregate(
        self,
        comparisons: (
            list[tuple[float, float]]
            | tuple[tuple[float, float], ...]
        ),
    ) -> LearningEffectivenessAggregate:
        if not comparisons:
            return LearningEffectivenessAggregate(
                total_observations=0,
                improved_count=0,
                regression_count=0,
                neutral_count=0,
                improvement_rate=0.0,
                regression_rate=0.0,
                average_improvement=0.0,
                average_confidence=0.0,
                consistently_improving=False,
            )

        evaluations = tuple(
            self.evaluator.evaluate(
                baseline_score=baseline,
                learned_score=learned,
            )
            for baseline, learned in comparisons
        )

        total = len(evaluations)

        improved = sum(
            1 for item in evaluations if item.improved
        )
        regression = sum(
            1 for item in evaluations if item.regression
        )
        neutral = sum(
            1 for item in evaluations if item.neutral
        )

        improvement_rate = (
            improved / total * 100.0
        )
        regression_rate = (
            regression / total * 100.0
        )

        average_improvement = (
            sum(item.improvement for item in evaluations)
            / total
        )

        average_confidence = (
            sum(item.confidence for item in evaluations)
            / total
        )

        consistently_improving = (
            total >= 3
            and improvement_rate >= 70.0
            and regression_rate < 20.0
            and average_improvement > 0.0
        )

        return LearningEffectivenessAggregate(
            total_observations=total,
            improved_count=improved,
            regression_count=regression,
            neutral_count=neutral,
            improvement_rate=improvement_rate,
            regression_rate=regression_rate,
            average_improvement=average_improvement,
            average_confidence=average_confidence,
            consistently_improving=consistently_improving,
        )
