from __future__ import annotations

from dataclasses import dataclass

from experience.learning_signal import LearningSignal


@dataclass(frozen=True)
class CrossTaskLearningProfile:
    task_family: str
    signals: tuple[LearningSignal, ...]
    strategies: tuple[str, ...]
    average_score: float
    successful_count: int
    failed_count: int


class CrossTaskLearning:
    """
    Group learning signals by an explicit task family.

    Cross-task reuse is opt-in through task_family. No task is inferred
    to be related merely because its text happens to look similar.
    """

    def build(
        self,
        *,
        task_family: str,
        signals: tuple[LearningSignal, ...]
        | list[LearningSignal],
    ) -> CrossTaskLearningProfile:
        family = task_family.strip()

        if not family:
            raise ValueError("task_family must not be empty")

        normalized = tuple(signals)

        successful = sum(
            1
            for signal in normalized
            if signal.signal_type.value.endswith("success")
        )

        failed = sum(
            1
            for signal in normalized
            if signal.signal_type.value.endswith("failure")
        )

        average_score = (
            sum(signal.score for signal in normalized)
            / len(normalized)
            if normalized
            else 0.0
        )

        strategies = tuple(
            sorted(
                {
                    signal.strategy.strip().lower()
                    for signal in normalized
                    if signal.strategy.strip()
                }
            )
        )

        return CrossTaskLearningProfile(
            task_family=family,
            signals=normalized,
            strategies=strategies,
            average_score=average_score,
            successful_count=successful,
            failed_count=failed,
        )

    def merge(
        self,
        profiles: tuple[CrossTaskLearningProfile, ...]
        | list[CrossTaskLearningProfile],
    ) -> tuple[CrossTaskLearningProfile, ...]:
        grouped: dict[str, list[LearningSignal]] = {}

        for profile in profiles:
            family = profile.task_family.strip()

            if not family:
                continue

            grouped.setdefault(family, []).extend(
                profile.signals
            )

        return tuple(
            self.build(
                task_family=family,
                signals=signals,
            )
            for family, signals in sorted(grouped.items())
        )
