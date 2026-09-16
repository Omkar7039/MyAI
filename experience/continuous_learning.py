from __future__ import annotations

from dataclasses import dataclass

from experience.learning_effectiveness import LearningEffectivenessEvaluator
from experience.learning_regression import LearningRegressionDetector
from experience.learning_rollback import LearningRollbackDecision, LearningRollbackPolicy


@dataclass(frozen=True)
class ContinuousLearningDecision:
    strategy: str
    baseline_score: float
    learned_score: float
    improved: bool
    regression_detected: bool
    rollback: bool
    severity: str
    reason: str


class ContinuousLearningController:
    def __init__(
        self,
        *,
        rollback_severity: str = "high",
        low_regression_threshold: float = 10.0,
        medium_regression_threshold: float = 25.0,
    ):
        self.effectiveness = LearningEffectivenessEvaluator()
        self.regression_detector = LearningRegressionDetector(
            low_threshold=low_regression_threshold,
            medium_threshold=medium_regression_threshold,
        )
        self.rollback_policy = LearningRollbackPolicy(
            rollback_severity=rollback_severity,
        )

    def evaluate(
        self,
        *,
        strategy: str,
        baseline_score: float,
        learned_score: float,
    ) -> ContinuousLearningDecision:
        name = strategy.strip()
        if not name:
            raise ValueError("strategy must not be empty")

        self._validate_score(baseline_score, "baseline_score")
        self._validate_score(learned_score, "learned_score")

        effectiveness = self.effectiveness.evaluate(
            baseline_score=baseline_score,
            learned_score=learned_score,
        )

        regression = self.regression_detector.detect(
            strategy=name,
            baseline_score=baseline_score,
            learned_score=learned_score,
        )

        rollback: LearningRollbackDecision = self.rollback_policy.decide(
            regression
        )

        if rollback.rollback:
            reason = rollback.reason
        elif effectiveness.improved:
            reason = "learned strategy improved over baseline"
        else:
            reason = effectiveness.reasons[0] if effectiveness.reasons else "no effectiveness change detected"

        return ContinuousLearningDecision(
            strategy=name,
            baseline_score=float(baseline_score),
            learned_score=float(learned_score),
            improved=effectiveness.improved,
            regression_detected=regression.detected,
            rollback=rollback.rollback,
            severity=regression.severity,
            reason=reason,
        )

    @staticmethod
    def _validate_score(value: float, field: str) -> None:
        if not 0.0 <= float(value) <= 100.0:
            raise ValueError(f"{field} must be between 0 and 100")
