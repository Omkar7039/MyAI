from __future__ import annotations

from dataclasses import dataclass

from experience.adaptive_strategy import AdaptiveStrategyScore
from experience.learning_effectiveness_aggregate import (
    LearningEffectivenessAggregate,
)


@dataclass(frozen=True)
class EffectivenessAwareStrategyScore:
    strategy: str
    score: float
    adaptive_score: float
    effectiveness_score: float
    improvement_rate: float
    regression_rate: float
    total_observations: int


class EffectivenessAwareRanker:
    """
    Combine adaptive strategy performance with repeated effectiveness.

    Score:
      adaptive strategy score   -> 60%
      effectiveness signal       -> 40%

    Effectiveness signal:
      improvement rate weighted by average improvement.

    A strategy with insufficient effectiveness evidence keeps a neutral
    effectiveness contribution rather than receiving an artificial bonus.
    """

    def rank(
        self,
        strategies: tuple[AdaptiveStrategyScore, ...]
        | list[AdaptiveStrategyScore],
        effectiveness_by_strategy: dict[
            str,
            LearningEffectivenessAggregate,
        ]
        | None = None,
    ) -> tuple[EffectivenessAwareStrategyScore, ...]:
        effectiveness_by_strategy = (
            effectiveness_by_strategy or {}
        )

        results: list[EffectivenessAwareStrategyScore] = []

        for strategy in strategies:
            name = strategy.strategy.strip().lower()
            effectiveness = effectiveness_by_strategy.get(name)

            if effectiveness is None:
                effectiveness_score = 0.0
                improvement_rate = 0.0
                regression_rate = 0.0
                observations = 0
            else:
                improvement_rate = effectiveness.improvement_rate
                regression_rate = effectiveness.regression_rate
                observations = effectiveness.total_observations

                improvement_factor = min(
                    max(
                        effectiveness.average_improvement,
                        0.0,
                    )
                    / 50.0,
                    1.0,
                )

                effectiveness_score = (
                    improvement_rate * 0.7
                    + improvement_factor * 100.0 * 0.3
                )

                if regression_rate >= 20.0:
                    effectiveness_score *= 0.5

            score = (
                strategy.score * 0.60
                + effectiveness_score * 0.40
            )

            results.append(
                EffectivenessAwareStrategyScore(
                    strategy=name,
                    score=max(0.0, min(100.0, score)),
                    adaptive_score=strategy.score,
                    effectiveness_score=effectiveness_score,
                    improvement_rate=improvement_rate,
                    regression_rate=regression_rate,
                    total_observations=observations,
                )
            )

        return tuple(
            sorted(
                results,
                key=lambda item: (
                    -item.score,
                    -item.effectiveness_score,
                    -item.adaptive_score,
                    item.strategy,
                ),
            )
        )

    def best(
        self,
        strategies: tuple[AdaptiveStrategyScore, ...]
        | list[AdaptiveStrategyScore],
        effectiveness_by_strategy: dict[
            str,
            LearningEffectivenessAggregate,
        ]
        | None = None,
    ) -> EffectivenessAwareStrategyScore | None:
        ranked = self.rank(
            strategies,
            effectiveness_by_strategy,
        )

        return ranked[0] if ranked else None
