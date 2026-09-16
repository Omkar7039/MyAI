from __future__ import annotations

from dataclasses import dataclass

from experience.learning_effectiveness_aggregate import (
    LearningEffectivenessAggregate,
)
from experience.learning_policy import (
    LearningPolicyDecision,
)


@dataclass(frozen=True)
class EffectivenessPolicyDecision:
    allowed: bool
    strategy: str | None
    confidence: float
    reason: str


class EffectivenessAwarePolicy:
    """
    Apply an additional effectiveness gate on top of the normal
    learning policy.

    Historical strategy evidence must first satisfy the ordinary
    learning policy and then demonstrate consistent improvement.
    """

    def __init__(
        self,
        *,
        min_improvement_rate: float = 70.0,
        max_regression_rate: float = 20.0,
        min_average_improvement: float = 0.0,
        min_observations: int = 3,
    ):
        if not 0.0 <= min_improvement_rate <= 100.0:
            raise ValueError(
                "min_improvement_rate must be between 0 and 100"
            )

        if not 0.0 <= max_regression_rate <= 100.0:
            raise ValueError(
                "max_regression_rate must be between 0 and 100"
            )

        if min_average_improvement < 0.0:
            raise ValueError(
                "min_average_improvement must be at least 0"
            )

        if min_observations < 1:
            raise ValueError(
                "min_observations must be at least 1"
            )

        self.min_improvement_rate = min_improvement_rate
        self.max_regression_rate = max_regression_rate
        self.min_average_improvement = min_average_improvement
        self.min_observations = min_observations

    def decide(
        self,
        *,
        learning_decision: LearningPolicyDecision,
        effectiveness: LearningEffectivenessAggregate,
    ) -> EffectivenessPolicyDecision:
        if not learning_decision.allowed:
            return EffectivenessPolicyDecision(
                allowed=False,
                strategy=learning_decision.strategy,
                confidence=0.0,
                reason=(
                    "base learning policy rejected strategy: "
                    f"{learning_decision.reason}"
                ),
            )

        if effectiveness.total_observations < self.min_observations:
            return EffectivenessPolicyDecision(
                allowed=False,
                strategy=learning_decision.strategy,
                confidence=effectiveness.average_confidence,
                reason=(
                    "insufficient effectiveness observations"
                ),
            )

        if (
            effectiveness.improvement_rate
            < self.min_improvement_rate
        ):
            return EffectivenessPolicyDecision(
                allowed=False,
                strategy=learning_decision.strategy,
                confidence=effectiveness.average_confidence,
                reason=(
                    "historical improvement rate is below "
                    "effectiveness threshold"
                ),
            )

        if (
            effectiveness.regression_rate
            >= self.max_regression_rate
        ):
            return EffectivenessPolicyDecision(
                allowed=False,
                strategy=learning_decision.strategy,
                confidence=effectiveness.average_confidence,
                reason=(
                    "historical regression rate is above "
                    "effectiveness threshold"
                ),
            )

        if (
            effectiveness.average_improvement <= 0.0
            or effectiveness.average_improvement
            < self.min_average_improvement
        ):
            return EffectivenessPolicyDecision(
                allowed=False,
                strategy=learning_decision.strategy,
                confidence=effectiveness.average_confidence,
                reason=(
                    "average historical improvement is not positive"
                ),
            )

        confidence = min(
            100.0,
            (
                learning_decision.confidence
                + effectiveness.average_confidence
            ) / 2.0,
        )

        return EffectivenessPolicyDecision(
            allowed=True,
            strategy=learning_decision.strategy,
            confidence=confidence,
            reason=(
                "strategy passed learning and effectiveness policies"
            ),
        )
