from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict

from experience.learning_signal import (
    LearningSignal,
    LearningSignalType,
)


@dataclass(frozen=True)
class StrategyFailureStats:
    strategy: str
    failures: int
    retries: int
    rollbacks: int
    total_negative_events: int
    failure_rate: float
    retry_rate: float
    rollback_rate: float


class FailedStrategyTracker:
    """
    Track negative strategy outcomes.

    Failure, retry, and rollback are deliberately kept as separate
    signals so later learning logic can distinguish:
      - a strategy that directly failed,
      - a strategy that eventually needed retry,
      - a strategy that required rollback.

    Successful outcomes are not counted as negative events.
    """

    def summarize(
        self,
        signals: tuple[LearningSignal, ...]
        | list[LearningSignal],
    ) -> tuple[StrategyFailureStats, ...]:
        grouped: dict[str, dict[str, int]] = defaultdict(
            lambda: {
                "failures": 0,
                "retries": 0,
                "rollbacks": 0,
            }
        )

        for signal in signals:
            strategy = signal.strategy.strip().lower()

            if not strategy:
                continue

            if signal.signal_type == LearningSignalType.REPAIR_FAILURE:
                grouped[strategy]["failures"] += 1

            elif signal.signal_type == LearningSignalType.VERIFICATION_FAILURE:
                grouped[strategy]["failures"] += 1

            elif signal.signal_type == LearningSignalType.RETRY:
                grouped[strategy]["retries"] += 1

            elif signal.signal_type == LearningSignalType.ROLLBACK:
                grouped[strategy]["rollbacks"] += 1

        results: list[StrategyFailureStats] = []

        for strategy in sorted(grouped):
            data = grouped[strategy]

            failures = data["failures"]
            retries = data["retries"]
            rollbacks = data["rollbacks"]

            negative_events = failures + retries + rollbacks

            failure_rate = (
                (failures / negative_events) * 100.0
                if negative_events
                else 0.0
            )

            retry_rate = (
                (retries / negative_events) * 100.0
                if negative_events
                else 0.0
            )

            rollback_rate = (
                (rollbacks / negative_events) * 100.0
                if negative_events
                else 0.0
            )

            results.append(
                StrategyFailureStats(
                    strategy=strategy,
                    failures=failures,
                    retries=retries,
                    rollbacks=rollbacks,
                    total_negative_events=negative_events,
                    failure_rate=failure_rate,
                    retry_rate=retry_rate,
                    rollback_rate=rollback_rate,
                )
            )

        return tuple(results)

    def rank(
        self,
        signals: tuple[LearningSignal, ...]
        | list[LearningSignal],
    ) -> tuple[StrategyFailureStats, ...]:
        stats = self.summarize(signals)

        return tuple(
            sorted(
                stats,
                key=lambda item: (
                    -item.rollback_rate,
                    -item.failure_rate,
                    -item.retry_rate,
                    -item.total_negative_events,
                    item.strategy,
                ),
            )
        )

    def worst(
        self,
        signals: tuple[LearningSignal, ...]
        | list[LearningSignal],
    ) -> StrategyFailureStats | None:
        ranked = self.rank(signals)

        return ranked[0] if ranked else None
