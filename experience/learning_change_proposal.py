from __future__ import annotations

from dataclasses import dataclass

from experience.adaptive_strategy import AdaptiveStrategyScore
from experience.learning_effectiveness import LearningEffectiveness
from experience.learning_regression import LearningRegression


@dataclass(frozen=True)
class LearningChangeProposal:
    strategy: str
    current_score: float
    proposed_score: float
    observations: int
    improvement: float
    improved: bool
    regression_detected: bool
    regression_severity: str
    confidence: float
    rationale: str


class LearningChangeProposalBuilder:
    """
    Build an immutable proposal for a potential learning change.

    A proposal is descriptive only. It does not approve, apply, persist,
    or rollback any learning change.
    """

    def build(
        self,
        *,
        candidate: AdaptiveStrategyScore,
        effectiveness: LearningEffectiveness,
        regression: LearningRegression,
    ) -> LearningChangeProposal:
        strategy = candidate.strategy.strip()

        if not strategy:
            raise ValueError("strategy must not be empty")

        if effectiveness.baseline_score != regression.baseline_score:
            raise ValueError(
                "effectiveness and regression baseline scores must match"
            )

        if effectiveness.learned_score != regression.learned_score:
            raise ValueError(
                "effectiveness and regression learned scores must match"
            )

        if regression.strategy != strategy:
            raise ValueError(
                "candidate and regression strategies must match"
            )

        rationale = self._rationale(
            effectiveness=effectiveness,
            regression=regression,
        )

        return LearningChangeProposal(
            strategy=strategy,
            current_score=effectiveness.baseline_score,
            proposed_score=effectiveness.learned_score,
            observations=candidate.total_outcomes,
            improvement=effectiveness.improvement,
            improved=effectiveness.improved,
            regression_detected=regression.detected,
            regression_severity=regression.severity,
            confidence=effectiveness.confidence,
            rationale=rationale,
        )

    @staticmethod
    def _rationale(
        *,
        effectiveness: LearningEffectiveness,
        regression: LearningRegression,
    ) -> str:
        if regression.detected:
            return (
                f"learned strategy regressed by "
                f"{regression.regression:.2f} points"
            )

        if effectiveness.improved:
            return (
                f"learned strategy improved by "
                f"{effectiveness.improvement:.2f} points"
            )

        return "learned strategy matched the baseline"
