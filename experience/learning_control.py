from __future__ import annotations

from dataclasses import dataclass

from experience.continuous_learning import (
    ContinuousLearningController,
    ContinuousLearningDecision,
)


@dataclass(frozen=True)
class LearningControlDecision:
    strategy: str
    allowed: bool
    rollback: bool
    improved: bool
    regression_detected: bool
    severity: str
    reason: str


class LearningControlAdapter:
    def __init__(
        self,
        controller: ContinuousLearningController | None = None,
    ):
        self.controller = controller or ContinuousLearningController()

    def evaluate(
        self,
        *,
        strategy: str,
        baseline_score: float,
        learned_score: float,
    ) -> LearningControlDecision:
        decision: ContinuousLearningDecision = self.controller.evaluate(
            strategy=strategy,
            baseline_score=baseline_score,
            learned_score=learned_score,
        )

        return LearningControlDecision(
            strategy=decision.strategy,
            allowed=not decision.rollback,
            rollback=decision.rollback,
            improved=decision.improved,
            regression_detected=decision.regression_detected,
            severity=decision.severity,
            reason=decision.reason,
        )
