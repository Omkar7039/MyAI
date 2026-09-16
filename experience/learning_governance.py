from __future__ import annotations

from dataclasses import dataclass

from experience.learning_approval import (
    LearningApprovalDecision,
    LearningApprovalPolicy,
)
from experience.learning_change_application import (
    LearningAppliedChange,
    LearningChangeApplication,
)
from experience.learning_change_proposal import (
    LearningChangeProposal,
)
from experience.learning_change_history import (
    LearningChangeHistory,
)
from experience.learning_change_validator import (
    LearningChangeProposalValidator,
)


@dataclass(frozen=True)
class LearningGovernanceDecision:
    approved: bool
    applied: bool
    strategy: str
    confidence: float
    reason: str
    change: LearningAppliedChange | None


class LearningGovernanceController:
    """
    Coordinate proposal validation, approval, and application.

    This controller does not persist history or perform rollback. Those
    responsibilities remain isolated in their dedicated components.
    """

    def __init__(
        self,
        *,
        validator: LearningChangeProposalValidator | None = None,
        approval: LearningApprovalPolicy | None = None,
        application: LearningChangeApplication | None = None,
        history: LearningChangeHistory | None = None,
    ):
        self.validator = (
            validator or LearningChangeProposalValidator()
        )
        self.approval = approval or LearningApprovalPolicy(
            validator=self.validator,
        )
        self.application = (
            application or LearningChangeApplication()
        )

        self.history = history

    def evaluate(
        self,
        proposal: LearningChangeProposal,
    ) -> LearningGovernanceDecision:
        validation = self.validator.validate(proposal)

        if not validation.valid:
            return LearningGovernanceDecision(
                approved=False,
                applied=False,
                strategy=proposal.strategy,
                confidence=proposal.confidence,
                reason=(
                    f"proposal validation failed: "
                    f"{validation.reason}"
                ),
                change=None,
            )

        approval: LearningApprovalDecision = self.approval.decide(
            proposal
        )

        if not approval.approved:
            return LearningGovernanceDecision(
                approved=False,
                applied=False,
                strategy=proposal.strategy,
                confidence=approval.confidence,
                reason=approval.reason,
                change=None,
            )

        change = self.application.apply(
            proposal=proposal,
            approval=approval,
        )

        if self.history is not None:
            self.history.record(
                proposal=proposal,
                approval=approval,
                applied=change,
            )

        return LearningGovernanceDecision(
            approved=True,
            applied=True,
            strategy=change.strategy,
            confidence=change.confidence,
            reason="learning change approved and applied",
            change=change,
        )

    def get_applied(
        self,
        strategy: str,
    ) -> LearningAppliedChange | None:
        return self.application.get(strategy)

    def all_applied(
        self,
    ) -> tuple[LearningAppliedChange, ...]:
        return self.application.all()

    def clear(self) -> None:
        self.application.clear()
