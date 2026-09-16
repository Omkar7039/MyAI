from __future__ import annotations

from dataclasses import dataclass

from experience.historical_learning_injection import (
    HistoricalLearningInjection,
)
from experience.learning_signal import LearningSignal


@dataclass(frozen=True)
class LearningDebugContext:
    task: str
    signals: tuple[LearningSignal, ...]
    strategies: tuple[str, ...]
    guidance: tuple[str, ...]


class LearningDebugContextBuilder:
    """
    Build advisory debugging context from historical learning.

    Historical learning never replaces current source, tests, or
    investigation evidence.
    """

    def build(
        self,
        *,
        task: str,
        injection: HistoricalLearningInjection,
    ) -> LearningDebugContext:
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
                f"Historical strategy {strategy!r} "
                f"has observed utility {utility:.2f}"
            )

        if not injection.signals:
            guidance.append(
                "No historical debugging experience is available"
            )

        guidance.append(
            "Use historical learning only as advisory context"
        )
        guidance.append(
            "Current source, tests, and investigation evidence "
            "take priority"
        )

        return LearningDebugContext(
            task=task.strip(),
            signals=injection.signals,
            strategies=strategies,
            guidance=tuple(guidance),
        )
