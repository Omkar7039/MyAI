from __future__ import annotations

from dataclasses import dataclass

from experience.learning_signal import LearningSignal


@dataclass(frozen=True)
class LearningSafetyDecision:
    allowed: bool
    signals: tuple[LearningSignal, ...]
    reason: str


class LearningSafetyGuard:
    """
    Prevent unsafe cross-task learning reuse.

    Rules:
      - only explicitly matching task families are allowed
      - empty requested families are rejected
      - empty signal sets are safe but unusable
      - signals without a task-family marker are rejected when a family
        is explicitly required
      - current-task signals may be used without cross-task filtering
    """

    def filter(
        self,
        *,
        task_family: str | None,
        signals: tuple[LearningSignal, ...]
        | list[LearningSignal],
        allow_cross_task: bool = False,
    ) -> LearningSafetyDecision:
        normalized = tuple(signals)

        if not normalized:
            return LearningSafetyDecision(
                allowed=False,
                signals=(),
                reason="no learning signals available",
            )

        family = (task_family or "").strip()

        if not allow_cross_task:
            return LearningSafetyDecision(
                allowed=True,
                signals=normalized,
                reason="cross-task learning is disabled",
            )

        if not family:
            return LearningSafetyDecision(
                allowed=False,
                signals=(),
                reason=(
                    "task family is required for cross-task learning"
                ),
            )

        matched: list[LearningSignal] = []

        for signal in normalized:
            signal_family = self._extract_family(
                signal.metadata
            )

            if signal_family == family:
                matched.append(signal)

        if not matched:
            return LearningSafetyDecision(
                allowed=False,
                signals=(),
                reason="no learning signals match the requested task family",
            )

        return LearningSafetyDecision(
            allowed=True,
            signals=tuple(matched),
            reason="learning signals match the requested task family",
        )

    @classmethod
    def _extract_family(cls, metadata: str) -> str:
        for part in metadata.split(";"):
            key, separator, value = part.partition("=")

            if not separator:
                continue

            key = key.strip().lower()
            value = value.strip()

            if key == "task_family":
                return value

            if key == "source_metadata":
                nested = cls._extract_family(value)
                if nested:
                    return nested

        return ""
