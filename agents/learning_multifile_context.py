from __future__ import annotations

from dataclasses import dataclass

from experience.historical_learning_injection import (
    HistoricalLearningInjection,
)
from experience.learning_signal import LearningSignal


@dataclass(frozen=True)
class LearningMultiFileContext:
    task: str
    signals: tuple[LearningSignal, ...]
    strategies: tuple[str, ...]
    guidance: tuple[str, ...]


class LearningMultiFileContextBuilder:
    """
    Build advisory context for autonomous multi-file repair.

    Historical learning does not replace current repository state,
    patch validation, regression checks, or rollback safeguards.
    """

    def build(
        self,
        *,
        task: str,
        injection: HistoricalLearningInjection,
    ) -> LearningMultiFileContext:
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
                f"Historical repair strategy {strategy!r} "
                f"has observed utility {utility:.2f}"
            )

        if not injection.signals:
            guidance.append(
                "No historical multi-file repair experience is available"
            )

        guidance.append(
            "Use historical learning only as advisory repair guidance"
        )
        guidance.append(
            "Current repository state and patch validation take priority"
        )
        guidance.append(
            "Regression verification and rollback safeguards remain mandatory"
        )

        return LearningMultiFileContext(
            task=task.strip(),
            signals=injection.signals,
            strategies=strategies,
            guidance=tuple(guidance),
        )
