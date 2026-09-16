from __future__ import annotations

from dataclasses import dataclass

from experience.continuous_learning import ContinuousLearningController
from experience.learning_change_application import (
    LearningAppliedChange,
    LearningChangeApplication,
)


@dataclass(frozen=True)
class AutomaticRollbackResult:
    strategy: str
    rollback_requested: bool
    rolled_back: bool
    severity: str
    restored: LearningAppliedChange | None
    reason: str


class AutomaticLearningRollback:
    """
    Evaluate a learned strategy against its baseline and automatically
    restore the previous applied learning state when rollback policy
    requires it.

    Rollback is attempted only when:
      1. continuous learning detects a rollback condition, and
      2. the strategy has rollback history available.

    No rollback is performed when the learned result is acceptable or
    when there is nothing to restore.
    """

    def __init__(
        self,
        *,
        controller: ContinuousLearningController | None = None,
        application: LearningChangeApplication | None = None,
    ):
        self.controller = (
            controller or ContinuousLearningController()
        )
        self.application = (
            application or LearningChangeApplication()
        )

    def evaluate(
        self,
        *,
        strategy: str,
        baseline_score: float,
        learned_score: float,
    ) -> AutomaticRollbackResult:
        name = strategy.strip().lower()

        if not name:
            raise ValueError("strategy must not be empty")

        decision = self.controller.evaluate(
            strategy=name,
            baseline_score=baseline_score,
            learned_score=learned_score,
        )

        if not decision.rollback:
            return AutomaticRollbackResult(
                strategy=name,
                rollback_requested=False,
                rolled_back=False,
                severity=decision.severity,
                restored=None,
                reason=decision.reason,
            )

        if not self.application.can_rollback(name):
            return AutomaticRollbackResult(
                strategy=name,
                rollback_requested=True,
                rolled_back=False,
                severity=decision.severity,
                restored=None,
                reason=(
                    f"{decision.reason}; "
                    "no rollback state is available"
                ),
            )

        restored = self.application.rollback(name)

        return AutomaticRollbackResult(
            strategy=name,
            rollback_requested=True,
            rolled_back=True,
            severity=decision.severity,
            restored=restored,
            reason=(
                f"{decision.reason}; "
                "previous learning state restored"
            ),
        )
