from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict

from experience.learning_signal import (
    LearningSignal,
    LearningSignalType,
)

@dataclass(frozen=True)
class AdaptiveStrategyScore:
    strategy: str
    score: float
    success_rate: float
    average_outcome_score: float
    utility_score: float
    failure_penalty: float
    total_outcomes: int


class AdaptiveStrategyRanker:
    """
    Rank strategies using observed outcomes and experience utility.

    The ranking is intentionally deterministic and advisory-only.

    Score components:
      success rate          -> 50%
      average outcome      -> 30%
      experience utility  -> 20%

    Negative adjustment:
      failure/retry/rollback profile
    """

    def rank(
        self,
        signals: tuple[LearningSignal, ...] | list[LearningSignal],
        utility_by_strategy: dict[str, float] | None = None,
    ) -> tuple[AdaptiveStrategyScore, ...]:
        utility_by_strategy = utility_by_strategy or {}

        outcomes: dict[str, list[LearningSignal]] = defaultdict(list)
        negative_events: dict[str, int] = defaultdict(int)

        for signal in signals:
            strategy = signal.strategy.strip().lower()

            if not strategy:
                continue

            if signal.signal_type in {
                LearningSignalType.REPAIR_SUCCESS,
                LearningSignalType.REPAIR_FAILURE,
                LearningSignalType.VERIFICATION_SUCCESS,
                LearningSignalType.VERIFICATION_FAILURE,
            }:
                outcomes[strategy].append(signal)

            elif signal.signal_type in {
                LearningSignalType.RETRY,
                LearningSignalType.ROLLBACK,
            }:
                negative_events[strategy] += 1

        results: list[AdaptiveStrategyScore] = []

        for strategy in sorted(outcomes):
            items = outcomes[strategy]

            successful = sum(
                1
                for item in items
                if item.signal_type in {
                    LearningSignalType.REPAIR_SUCCESS,
                    LearningSignalType.VERIFICATION_SUCCESS,
                }
            )

            total = len(items)

            success_rate = (
                (successful / total) * 100.0
                if total
                else 0.0
            )

            average_outcome_score = (
                sum(item.score for item in items) / total
                if total
                else 0.0
            )

            utility_score = max(
                0.0,
                min(
                    100.0,
                    float(
                        utility_by_strategy.get(strategy, 0.0)
                    ),
                ),
            )

            failure_penalty = min(
                negative_events[strategy] * 5.0,
                20.0,
            )

            score = max(
                0.0,
                min(
                    100.0,
                    (
                        success_rate * 0.50
                        + average_outcome_score * 0.30
                        + utility_score * 0.20
                        - failure_penalty
                    ),
                ),
            )

            results.append(
                AdaptiveStrategyScore(
                    strategy=strategy,
                    score=score,
                    success_rate=success_rate,
                    average_outcome_score=average_outcome_score,
                    utility_score=utility_score,
                    failure_penalty=failure_penalty,
                    total_outcomes=total,
                )
            )

        return tuple(
            sorted(
                results,
                key=lambda item: (
                    -item.score,
                    -item.success_rate,
                    -item.average_outcome_score,
                    item.strategy,
                ),
            )
        )

    def best(
        self,
        signals: tuple[LearningSignal, ...] | list[LearningSignal],
        utility_by_strategy: dict[str, float] | None = None,
    ) -> AdaptiveStrategyScore | None:
        ranked = self.rank(
            signals,
            utility_by_strategy,
        )

        return ranked[0] if ranked else None
