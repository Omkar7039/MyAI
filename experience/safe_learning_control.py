from __future__ import annotations

from dataclasses import dataclass

from experience.learning_control import LearningControlAdapter
from experience.learning_signal import LearningSignal
from experience.learning_safety import LearningSafetyGuard


@dataclass(frozen=True)
class SafeLearningControlDecision:
    allowed: bool
    rollback: bool
    strategy: str
    severity: str
    confidence: float
    reason: str
    signals: tuple[LearningSignal, ...]


class SafeLearningControl:
    """
    Combine cross-task learning safety with effectiveness/rollback control.

    Safety is evaluated before learned-strategy control. If the historical
    evidence is unsafe for the requested task family, the learned strategy
    is blocked without running the effectiveness decision.
    """

    def __init__(
        self,
        *,
        safety: LearningSafetyGuard | None = None,
        control: LearningControlAdapter | None = None,
    ):
        self.safety = safety or LearningSafetyGuard()
        self.control = control or LearningControlAdapter()

    def evaluate(
        self,
        *,
        strategy: str,
        signals: tuple[LearningSignal, ...]
        | list[LearningSignal],
        task_family: str | None = None,
        allow_cross_task: bool = False,
        baseline_score: float,
        learned_score: float,
    ) -> SafeLearningControlDecision:
        name = strategy.strip()

        if not name:
            raise ValueError("strategy must not be empty")

        safety_decision = self.safety.filter(
            task_family=task_family,
            signals=signals,
            allow_cross_task=allow_cross_task,
        )

        if not safety_decision.allowed:
            return SafeLearningControlDecision(
                allowed=False,
                rollback=False,
                strategy=name,
                severity="none",
                confidence=0.0,
                reason=(
                    f"learning safety blocked strategy: "
                    f"{safety_decision.reason}"
                ),
                signals=(),
            )

        control_decision = self.control.evaluate(
            strategy=name,
            baseline_score=baseline_score,
            learned_score=learned_score,
        )

        return SafeLearningControlDecision(
            allowed=control_decision.allowed,
            rollback=control_decision.rollback,
            strategy=control_decision.strategy,
            severity=control_decision.severity,
            confidence=100.0 if control_decision.improved else 0.0,
            reason=control_decision.reason,
            signals=safety_decision.signals,
        )
