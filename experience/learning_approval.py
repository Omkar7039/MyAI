from __future__ import annotations

from dataclasses import dataclass

from experience.learning_change_proposal import LearningChangeProposal
from experience.learning_change_validator import (
    LearningChangeProposalValidator,
)


@dataclass(frozen=True)
class LearningApprovalDecision:
    approved: bool
    strategy: str
    confidence: float
    reason: str


class LearningApprovalPolicy:
    """
    Decide whether a validated learning change may be adopted.

    Approval requires:
      - structurally valid proposal
      - minimum observations
      - genuine improvement
      - no detected regression
      - minimum confidence
    """

    def __init__(
        self,
        *,
        min_observations: int = 3,
        min_improvement: float = 0.0,
        min_confidence: float = 50.0,
        validator: LearningChangeProposalValidator | None = None,
    ):
        if min_observations < 1:
            raise ValueError(
                "min_observations must be at least 1"
            )

        if min_improvement < 0.0:
            raise ValueError(
                "min_improvement must be at least 0"
            )

        if not 0.0 <= min_confidence <= 100.0:
            raise ValueError(
                "min_confidence must be between 0 and 100"
            )

        self.min_observations = min_observations
        self.min_improvement = float(min_improvement)
        self.min_confidence = float(min_confidence)
        self.validator = validator or LearningChangeProposalValidator()

    def decide(
        self,
        proposal: LearningChangeProposal,
    ) -> LearningApprovalDecision:
        validation = self.validator.validate(proposal)

        if not validation.valid:
            return LearningApprovalDecision(
                approved=False,
                strategy=proposal.strategy,
                confidence=proposal.confidence,
                reason=(
                    f"proposal validation failed: "
                    f"{validation.reason}"
                ),
            )

        if proposal.observations < self.min_observations:
            return LearningApprovalDecision(
                approved=False,
                strategy=proposal.strategy,
                confidence=proposal.confidence,
                reason="insufficient observations for learning approval",
            )

        if not proposal.improved:
            return LearningApprovalDecision(
                approved=False,
                strategy=proposal.strategy,
                confidence=proposal.confidence,
                reason="learning proposal does not improve the baseline",
            )

        if proposal.improvement < self.min_improvement:
            return LearningApprovalDecision(
                approved=False,
                strategy=proposal.strategy,
                confidence=proposal.confidence,
                reason="learning improvement is below approval threshold",
            )

        if proposal.regression_detected:
            return LearningApprovalDecision(
                approved=False,
                strategy=proposal.strategy,
                confidence=proposal.confidence,
                reason=(
                    "learning proposal contains a detected regression"
                ),
            )

        if proposal.confidence < self.min_confidence:
            return LearningApprovalDecision(
                approved=False,
                strategy=proposal.strategy,
                confidence=proposal.confidence,
                reason="learning confidence is below approval threshold",
            )

        return LearningApprovalDecision(
            approved=True,
            strategy=proposal.strategy,
            confidence=proposal.confidence,
            reason="learning proposal approved for adoption",
        )
