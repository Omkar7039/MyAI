from __future__ import annotations

from dataclasses import dataclass

from experience.learning_change_proposal import LearningChangeProposal


@dataclass(frozen=True)
class LearningChangeValidation:
    valid: bool
    reason: str


class LearningChangeProposalValidator:
    """
    Validate a learning change proposal before approval.

    Validation is structural and safety-oriented only. This component does
    not apply, persist, approve, or rollback a learning change.
    """

    def validate(
        self,
        proposal: LearningChangeProposal,
    ) -> LearningChangeValidation:
        if not proposal.strategy.strip():
            return LearningChangeValidation(
                valid=False,
                reason="strategy must not be empty",
            )

        if not 0.0 <= proposal.current_score <= 100.0:
            return LearningChangeValidation(
                valid=False,
                reason="current_score must be between 0 and 100",
            )

        if not 0.0 <= proposal.proposed_score <= 100.0:
            return LearningChangeValidation(
                valid=False,
                reason="proposed_score must be between 0 and 100",
            )

        if proposal.observations < 1:
            return LearningChangeValidation(
                valid=False,
                reason="observations must be at least 1",
            )

        expected_improvement = (
            proposal.proposed_score - proposal.current_score
        )

        if abs(proposal.improvement - expected_improvement) > 1e-9:
            return LearningChangeValidation(
                valid=False,
                reason="improvement does not match proposal scores",
            )

        if not 0.0 <= proposal.confidence <= 100.0:
            return LearningChangeValidation(
                valid=False,
                reason="confidence must be between 0 and 100",
            )

        if proposal.regression_detected:
            if proposal.regression_severity == "none":
                return LearningChangeValidation(
                    valid=False,
                    reason=(
                        "regression severity cannot be none when "
                        "regression is detected"
                    ),
                )

            if proposal.improvement >= 0.0:
                return LearningChangeValidation(
                    valid=False,
                    reason=(
                        "regression proposal must have negative "
                        "improvement"
                    ),
                )

        if not proposal.regression_detected:
            if proposal.regression_severity != "none":
                return LearningChangeValidation(
                    valid=False,
                    reason=(
                        "regression severity must be none when "
                        "regression is not detected"
                    ),
                )

            if proposal.improvement < 0.0:
                return LearningChangeValidation(
                    valid=False,
                    reason=(
                        "non-regression proposal cannot have negative "
                        "improvement"
                    ),
                )

        return LearningChangeValidation(
            valid=True,
            reason="learning change proposal is structurally valid",
        )
