from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict

from experience.learning_signal import (
    LearningSignal,
    LearningSignalType,
)


@dataclass(frozen=True)
class StrategyStats:
    strategy: str
    successful: int
    failed: int
    total: int
    success_rate: float
    average_score: float


class SuccessfulStrategyTracker:
    """
    Track strategy outcomes from learning signals.

    Only explicit repair/verification success and failure signals affect
    the statistics. Retries and rollbacks are retained as context by
    other learning components and are not counted as standalone outcomes.
    """

    SUCCESS_TYPES = {
        LearningSignalType.REPAIR_SUCCESS,
        LearningSignalType.VERIFICATION_SUCCESS,
    }

    FAILURE_TYPES = {
        LearningSignalType.REPAIR_FAILURE,
        LearningSignalType.VERIFICATION_FAILURE,
    }

    def summarize(
        self,
        signals: tuple[LearningSignal, ...]
        | list[LearningSignal],
    ) -> tuple[StrategyStats, ...]:
        grouped: dict[str, list[LearningSignal]] = defaultdict(list)

        for signal in signals:
            strategy = signal.strategy.strip().lower()

            if not strategy:
                continue

            if (
                signal.signal_type in self.SUCCESS_TYPES
                or signal.signal_type in self.FAILURE_TYPES
            ):
                grouped[strategy].append(signal)

        results: list[StrategyStats] = []

        for strategy in sorted(grouped):
            items = grouped[strategy]

            successful = sum(
                1
                for item in items
                if item.signal_type in self.SUCCESS_TYPES
            )

            failed = sum(
                1
                for item in items
                if item.signal_type in self.FAILURE_TYPES
            )

            total = successful + failed

            success_rate = (
                (successful / total) * 100.0
                if total
                else 0.0
            )

            average_score = (
                sum(item.score for item in items) / total
                if total
                else 0.0
            )

            results.append(
                StrategyStats(
                    strategy=strategy,
                    successful=successful,
                    failed=failed,
                    total=total,
                    success_rate=success_rate,
                    average_score=average_score,
                )
            )

        return tuple(results)

    def rank(
        self,
        signals: tuple[LearningSignal, ...]
        | list[LearningSignal],
    ) -> tuple[StrategyStats, ...]:
        stats = self.summarize(signals)

        return tuple(
            sorted(
                stats,
                key=lambda item: (
                    -item.success_rate,
                    -item.average_score,
                    -item.successful,
                    item.strategy,
                ),
            )
        )

    def best(
        self,
        signals: tuple[LearningSignal, ...]
        | list[LearningSignal],
    ) -> StrategyStats | None:
        ranked = self.rank(signals)

        return ranked[0] if ranked else None
