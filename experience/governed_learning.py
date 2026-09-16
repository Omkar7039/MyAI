from __future__ import annotations

from dataclasses import dataclass

from experience.adaptive_strategy import AdaptiveStrategyRanker
from experience.learning_change_proposal import (
    LearningChangeProposal,
    LearningChangeProposalBuilder,
)
from experience.learning_effectiveness import (
    LearningEffectivenessEvaluator,
)
from experience.learning_governance import (
    LearningGovernanceController,
    LearningGovernanceDecision,
)
from experience.learning_regression import (
    LearningRegressionDetector,
)
from experience.learning_signal import LearningSignal
from experience.learning_safety import LearningSafetyGuard


@dataclass(frozen=True)
class GovernedLearningResult:
    candidate_strategy: str | None
    proposal: LearningChangeProposal | None
    governance: LearningGovernanceDecision | None
    safe: bool
    reason: str


class GovernedLearningAdapter:
    """
    Build and evaluate a governed learning change from historical signals.

    This adapter is deterministic and side-effect-free except for the
    in-memory application performed by LearningGovernanceController.
    """

    def __init__(
        self,
        *,
        ranker: AdaptiveStrategyRanker | None = None,
        safety: LearningSafetyGuard | None = None,
        proposal_builder: LearningChangeProposalBuilder | None = None,
        effectiveness: LearningEffectivenessEvaluator | None = None,
        regression: LearningRegressionDetector | None = None,
        governance: LearningGovernanceController | None = None,
    ):
        self.ranker = ranker or AdaptiveStrategyRanker()
        self.safety = safety or LearningSafetyGuard()
        self.proposal_builder = (
            proposal_builder or LearningChangeProposalBuilder()
        )
        self.effectiveness = (
            effectiveness or LearningEffectivenessEvaluator()
        )
        self.regression = regression or LearningRegressionDetector()
        self.governance = (
            governance or LearningGovernanceController()
        )

    def evaluate(
        self,
        *,
        signals: tuple[LearningSignal, ...]
        | list[LearningSignal],
        baseline_score: float,
        task_family: str | None = None,
        allow_cross_task: bool = False,
        utility_by_strategy: dict[str, float] | None = None,
    ) -> GovernedLearningResult:
        safety = self.safety.filter(
            task_family=task_family,
            signals=signals,
            allow_cross_task=allow_cross_task,
        )

        if not safety.allowed:
            return GovernedLearningResult(
                candidate_strategy=None,
                proposal=None,
                governance=None,
                safe=False,
                reason=safety.reason,
            )

        ranked = self.ranker.rank(
            safety.signals,
            utility_by_strategy,
        )

        if not ranked:
            return GovernedLearningResult(
                candidate_strategy=None,
                proposal=None,
                governance=None,
                safe=True,
                reason="no historical strategy candidate available",
            )

        candidate = ranked[0]

        effectiveness = self.effectiveness.evaluate(
            baseline_score=baseline_score,
            learned_score=candidate.score,
        )

        regression = self.regression.detect(
            strategy=candidate.strategy,
            baseline_score=baseline_score,
            learned_score=candidate.score,
        )

        proposal = self.proposal_builder.build(
            candidate=candidate,
            effectiveness=effectiveness,
            regression=regression,
        )

        governance = self.governance.evaluate(proposal)

        return GovernedLearningResult(
            candidate_strategy=candidate.strategy,
            proposal=proposal,
            governance=governance,
            safe=True,
            reason=governance.reason,
        )
