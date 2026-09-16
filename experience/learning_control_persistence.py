from __future__ import annotations

from dataclasses import dataclass

from experience.learning_control import LearningControlAdapter
from experience.learning_persistence import (
    LearningPersistenceBridge,
    LearningPersistenceResult,
)
from experience.learning_signal import LearningSignal


@dataclass(frozen=True)
class ControlledPersistenceResult:
    allowed: bool
    rollback: bool
    reason: str
    persistence: LearningPersistenceResult | None


class ControlledLearningPersistence:
    """
    Persist learning evidence only when the learned strategy passes
    the learning control gate.

    Existing LearningPersistenceBridge behavior remains unchanged.
    """

    def __init__(
        self,
        persistence: LearningPersistenceBridge,
        control: LearningControlAdapter | None = None,
    ):
        self.persistence = persistence
        self.control = control or LearningControlAdapter()

    def persist(
        self,
        *,
        signals: tuple[LearningSignal, ...]
        | list[LearningSignal],
        strategy: str,
        baseline_score: float,
        learned_score: float,
    ) -> ControlledPersistenceResult:
        name = strategy.strip()

        if not name:
            raise ValueError("strategy must not be empty")

        control = self.control.evaluate(
            strategy=name,
            baseline_score=baseline_score,
            learned_score=learned_score,
        )

        if not control.allowed:
            return ControlledPersistenceResult(
                allowed=False,
                rollback=True,
                reason=control.reason,
                persistence=None,
            )

        result = self.persistence.persist(signals)

        return ControlledPersistenceResult(
            allowed=True,
            rollback=False,
            reason=control.reason,
            persistence=result,
        )
