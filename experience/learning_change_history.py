from __future__ import annotations

import hashlib
from dataclasses import dataclass

from experience.learning_approval import LearningApprovalDecision
from experience.learning_state import LearningAppliedChange
from experience.learning_change_proposal import LearningChangeProposal
from experience.store import Experience, ExperienceStore


@dataclass(frozen=True)
class LearningChangeHistoryResult:
    persisted: bool
    experience_id: str


class LearningChangeHistory:
    """
    Persist successfully approved and applied learning changes.

    History is append-safe through deterministic IDs. Repeated recording
    of the same applied change does not create duplicate records.
    """

    CATEGORY = "learning_change"

    def __init__(self, store: ExperienceStore):
        self.store = store

    def record(
        self,
        *,
        proposal: LearningChangeProposal,
        approval: LearningApprovalDecision,
        applied: LearningAppliedChange,
    ) -> LearningChangeHistoryResult:
        if not approval.approved:
            raise ValueError(
                "cannot record an unapproved learning change"
            )

        if proposal.strategy != applied.strategy:
            raise ValueError(
                "proposal and applied change strategies must match"
            )

        if approval.strategy != applied.strategy:
            raise ValueError(
                "approval and applied change strategies must match"
            )

        experience_id = self._experience_id(
            proposal=proposal,
            applied=applied,
        )

        if self.store.get(experience_id) is not None:
            return LearningChangeHistoryResult(
                persisted=False,
                experience_id=experience_id,
            )

        experience = Experience(
            experience_id=experience_id,
            task=f"learning change: {proposal.strategy}",
            category=self.CATEGORY,
            action="apply",
            outcome="approved",
            success=True,
            lesson=(
                f"Applied {proposal.strategy}: "
                f"{proposal.current_score:.2f} -> "
                f"{proposal.proposed_score:.2f}"
            ),
            metadata=self._metadata(
                proposal=proposal,
                approval=approval,
                applied=applied,
            ),
        )

        self.store.add(experience)

        return LearningChangeHistoryResult(
            persisted=True,
            experience_id=experience_id,
        )

    def recent(
        self,
        limit: int = 20,
    ) -> list[Experience]:
        return [
            item
            for item in self.store.recent(limit)
            if item.category == self.CATEGORY
        ]

    def get(
        self,
        experience_id: str,
    ) -> Experience | None:
        experience = self.store.get(experience_id)

        if experience is None:
            return None

        if experience.category != self.CATEGORY:
            return None

        return experience

    @staticmethod
    def _experience_id(
        *,
        proposal: LearningChangeProposal,
        applied: LearningAppliedChange,
    ) -> str:
        payload = "|".join(
            [
                proposal.strategy,
                f"{proposal.current_score:.6f}",
                f"{proposal.proposed_score:.6f}",
                str(proposal.observations),
                f"{proposal.confidence:.6f}",
                f"{applied.applied_score:.6f}",
                (
                    f"{applied.previous_score:.6f}"
                    if applied.previous_score is not None
                    else ""
                ),
            ]
        )

        digest = hashlib.sha256(
            payload.encode("utf-8")
        ).hexdigest()[:24]

        return f"learning-change-{digest}"

    @staticmethod
    def _metadata(
        *,
        proposal: LearningChangeProposal,
        approval: LearningApprovalDecision,
        applied: LearningAppliedChange,
    ) -> str:
        return "; ".join(
            [
                f"strategy={proposal.strategy}",
                f"previous_score={applied.previous_score}",
                f"applied_score={applied.applied_score:.2f}",
                f"observations={proposal.observations}",
                f"proposal_confidence={proposal.confidence:.2f}",
                f"approval_confidence={approval.confidence:.2f}",
                f"improvement={proposal.improvement:.2f}",
            ]
        )
