from __future__ import annotations

from dataclasses import dataclass

from experience.learning_persistence import (
    LearningPersistenceBridge,
    LearningPersistenceResult,
)
from experience.outcome_capture import CapturedOutcome
from experience.store import ExperienceStore


@dataclass(frozen=True)
class AutomaticPersistenceResult:
    captured: CapturedOutcome
    persistence: LearningPersistenceResult
    persisted: bool


class AutomaticLearningPersistence:
    """
    Persist automatically captured learning outcomes.

    This component connects outcome capture to the existing
    LearningPersistenceBridge. It does not make routing decisions and
    does not invoke model inference.
    """

    def __init__(
        self,
        store: ExperienceStore,
        *,
        persistence_bridge: LearningPersistenceBridge | None = None,
    ):
        self.persistence_bridge = (
            persistence_bridge
            or LearningPersistenceBridge(store)
        )

    def persist(
        self,
        captured: CapturedOutcome,
    ) -> AutomaticPersistenceResult:
        if not captured.captured:
            return AutomaticPersistenceResult(
                captured=captured,
                persistence=LearningPersistenceResult(
                    persisted=0,
                    skipped=0,
                    experience_ids=(),
                ),
                persisted=False,
            )

        result = self.persistence_bridge.persist(
            captured.feedback.signals
        )

        return AutomaticPersistenceResult(
            captured=captured,
            persistence=result,
            persisted=result.persisted > 0,
        )
