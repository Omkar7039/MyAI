from __future__ import annotations

from dataclasses import dataclass

from experience.historical_learning_injection import (
    HistoricalLearningInjection,
)
from experience.learning_signal import LearningSignal


@dataclass(frozen=True)
class LearningVerificationContext:
    task: str
    signals: tuple[LearningSignal, ...]
    strategies: tuple[str, ...]
    guidance: tuple[str, ...]


class LearningVerificationContextBuilder:
    """
    Build advisory verification context from historical learning.

    Historical verification experience can guide strategy choice, but
    current tests, mutation results, and verification evidence remain
    authoritative.
    """

    def build(
        self,
        *,
        task: str,
        injection: HistoricalLearningInjection,
    ) -> LearningVerificationContext:
        if not task.strip():
            raise ValueError("task must not be empty")

        strategies = tuple(
            sorted(
                {
                    signal.strategy.strip().lower()
                    for signal in injection.signals
                    if signal.strategy.strip()
                }
            )
        )

        guidance: list[str] = []

        for strategy in strategies:
            utility = injection.utility_by_strategy.get(
                strategy,
                0.0,
            )

            guidance.append(
                f"Historical verification strategy {strategy!r} "
                f"has observed utility {utility:.2f}"
            )

        if not injection.signals:
            guidance.append(
                "No historical verification experience is available"
            )

        guidance.append(
            "Use historical learning only as advisory verification guidance"
        )
        guidance.append(
            "Current tests and verification evidence take priority"
        )
        guidance.append(
            "Mutation and property verification remain authoritative"
        )

        return LearningVerificationContext(
            task=task.strip(),
            signals=injection.signals,
            strategies=strategies,
            guidance=tuple(guidance),
        )
