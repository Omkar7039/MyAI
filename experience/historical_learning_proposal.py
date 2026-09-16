from __future__ import annotations

from dataclasses import dataclass

from experience.adaptive_strategy import AdaptiveStrategyRanker
from experience.historical_learning import (
    HistoricalLearningRetriever,
    HistoricalLearningResult,
)
from experience.learning_change_proposal import (
    LearningChangeProposal,
    LearningChangeProposalBuilder,
)
from experience.learning_effectiveness import (
    LearningEffectivenessEvaluator,
)
from experience.learning_regression import (
    LearningRegressionDetector,
)


@dataclass(frozen=True)
class HistoricalProposalResult:
    proposal: LearningChangeProposal | None
    candidate_strategy: str | None
    retrieved: int
    source_experience_ids: tuple[str, ...]
    reason: str


class HistoricalLearningProposalGenerator:
    """
    Convert historical learning evidence into a learning change proposal.

    This component only retrieves, ranks, evaluates, and builds a proposal.
    It does not approve, apply, persist, or rollback the change.
    """

    def __init__(
        self,
        retriever: HistoricalLearningRetriever,
        *,
        ranker: AdaptiveStrategyRanker | None = None,
        effectiveness: LearningEffectivenessEvaluator | None = None,
        regression: LearningRegressionDetector | None = None,
        proposal_builder: LearningChangeProposalBuilder | None = None,
    ):
        self.retriever = retriever
        self.ranker = ranker or AdaptiveStrategyRanker()
        self.effectiveness = (
            effectiveness or LearningEffectivenessEvaluator()
        )
        self.regression = regression or LearningRegressionDetector()
        self.proposal_builder = (
            proposal_builder or LearningChangeProposalBuilder()
        )

    def recent(
        self,
        *,
        baseline_score: float,
        limit: int = 20,
        utility_by_strategy: dict[str, float] | None = None,
    ) -> HistoricalProposalResult:
        history = self.retriever.recent(limit)

        return self._build(
            history=history,
            baseline_score=baseline_score,
            utility_by_strategy=utility_by_strategy,
        )

    def search(
        self,
        *,
        query: str,
        baseline_score: float,
        limit: int = 10,
        utility_by_strategy: dict[str, float] | None = None,
    ) -> HistoricalProposalResult:
        history = self.retriever.search(query, limit)

        return self._build(
            history=history,
            baseline_score=baseline_score,
            utility_by_strategy=utility_by_strategy,
        )

    def _build(
        self,
        *,
        history: HistoricalLearningResult,
        baseline_score: float,
        utility_by_strategy: dict[str, float] | None,
    ) -> HistoricalProposalResult:
        if not history.signals:
            return HistoricalProposalResult(
                proposal=None,
                candidate_strategy=None,
                retrieved=history.retrieved,
                source_experience_ids=history.source_experience_ids,
                reason="no historical learning evidence available",
            )

        ranked = self.ranker.rank(
            history.signals,
            utility_by_strategy,
        )

        if not ranked:
            return HistoricalProposalResult(
                proposal=None,
                candidate_strategy=None,
                retrieved=history.retrieved,
                source_experience_ids=history.source_experience_ids,
                reason="historical evidence contains no usable strategy",
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

        return HistoricalProposalResult(
            proposal=proposal,
            candidate_strategy=candidate.strategy,
            retrieved=history.retrieved,
            source_experience_ids=history.source_experience_ids,
            reason="historical evidence converted into learning proposal",
        )
