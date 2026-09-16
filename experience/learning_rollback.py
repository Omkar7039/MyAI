from __future__ import annotations

from dataclasses import dataclass

from experience.learning_regression import LearningRegression


@dataclass(frozen=True)
class LearningRollbackDecision:
    strategy: str
    rollback: bool
    severity: str
    reason: str


class LearningRollbackPolicy:
    def __init__(
        self,
        *,
        rollback_severity: str = "high",
    ):
        allowed = {"low", "medium", "high"}

        severity = rollback_severity.strip().lower()
        if severity not in allowed:
            raise ValueError(
                "rollback_severity must be one of: low, medium, high"
            )

        self.rollback_severity = severity

    def decide(
        self,
        regression: LearningRegression,
    ) -> LearningRollbackDecision:
        if not regression.strategy.strip():
            raise ValueError("strategy must not be empty")

        if regression.severity == "none":
            return LearningRollbackDecision(
                strategy=regression.strategy,
                rollback=False,
                severity=regression.severity,
                reason="no learning regression detected",
            )

        severity_order = {
            "low": 1,
            "medium": 2,
            "high": 3,
        }

        detected_level = severity_order[regression.severity]
        rollback_level = severity_order[self.rollback_severity]

        should_rollback = detected_level >= rollback_level

        if should_rollback:
            reason = (
                f"learning regression severity {regression.severity} "
                f"meets rollback threshold {self.rollback_severity}"
            )
        else:
            reason = (
                f"learning regression severity {regression.severity} "
                f"is below rollback threshold {self.rollback_severity}"
            )

        return LearningRollbackDecision(
            strategy=regression.strategy,
            rollback=should_rollback,
            severity=regression.severity,
            reason=reason,
        )
