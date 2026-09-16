from __future__ import annotations

import hashlib
from dataclasses import dataclass

from experience.learning_signal import LearningSignal
from experience.store import Experience, ExperienceStore


@dataclass(frozen=True)
class LearningPersistenceResult:
    persisted: int
    skipped: int
    experience_ids: tuple[str, ...]


class LearningPersistenceBridge:
    """
    Persist learning signals into the existing ExperienceStore.

    Learning signals remain normalized observations. Persistence converts
    them into ordinary experience records while preserving provenance
    in metadata.
    """

    def __init__(
        self,
        store: ExperienceStore,
    ):
        self.store = store

    def persist(
        self,
        signals: tuple[LearningSignal, ...]
        | list[LearningSignal],
    ) -> LearningPersistenceResult:
        persisted = 0
        skipped = 0
        experience_ids: list[str] = []

        for signal in signals:
            experience_id = self._experience_id(signal)

            if self.store.get(experience_id) is not None:
                skipped += 1
                experience_ids.append(experience_id)
                continue

            experience = Experience(
                experience_id=experience_id,
                task=signal.task,
                category="learning",
                action=signal.signal_type.value,
                outcome=(
                    "success"
                    if signal.signal_type.value.endswith("success")
                    else signal.signal_type.value
                ),
                success=signal.signal_type.value.endswith("success"),
                lesson=self._lesson(signal),
                metadata=self._metadata(signal),
            )

            self.store.add(experience)
            persisted += 1
            experience_ids.append(experience_id)

        return LearningPersistenceResult(
            persisted=persisted,
            skipped=skipped,
            experience_ids=tuple(experience_ids),
        )

    @staticmethod
    def _experience_id(signal: LearningSignal) -> str:
        payload = "|".join(
            [
                signal.signal_type.value,
                signal.task,
                signal.strategy,
                str(signal.attempts),
                f"{signal.score:.6f}",
                signal.metadata,
            ]
        )

        digest = hashlib.sha256(
            payload.encode("utf-8")
        ).hexdigest()[:24]

        return f"learning-{digest}"

    @staticmethod
    def _lesson(signal: LearningSignal) -> str:
        strategy = signal.strategy or "unspecified"

        return (
            f"{signal.signal_type.value} using strategy "
            f"{strategy} produced score {signal.score:.2f}"
        )

    @staticmethod
    def _metadata(signal: LearningSignal) -> str:
        parts = [
            f"strategy={signal.strategy}",
            f"attempts={signal.attempts}",
            f"score={signal.score:.2f}",
        ]

        if signal.metadata:
            parts.append(
                f"source_metadata={signal.metadata}"
            )

        return "; ".join(parts)
