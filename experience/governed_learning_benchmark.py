from __future__ import annotations

from dataclasses import dataclass

from experience.automatic_learning_rollback import (
    AutomaticLearningRollback,
)
from experience.learning_approval import LearningApprovalDecision
from experience.learning_change_application import (
    LearningChangeApplication,
)
from experience.learning_change_history import (
    LearningChangeHistory,
)
from experience.learning_change_proposal import (
    LearningChangeProposal,
)
from experience.learning_governance import (
    LearningGovernanceController,
)
from experience.store import ExperienceStore


@dataclass(frozen=True)
class GovernedLearningBenchmarkResult:
    name: str
    passed: bool
    detail: str


class GovernedLearningBenchmark:
    """
    Deterministic benchmark for governed learning lifecycle.

    Covers:
      proposal
      validation
      approval
      application
      history persistence
      regression detection
      automatic rollback
    """

    def run(self) -> tuple[GovernedLearningBenchmarkResult, ...]:
        return (
            self._case_approval_and_application(),
            self._case_rejected_change(),
            self._case_history_persistence(),
            self._case_automatic_rollback(),
            self._case_first_change_rollback(),
        )

    def assert_all_pass(self) -> None:
        results = self.run()

        failed = [
            result
            for result in results
            if not result.passed
        ]

        if failed:
            details = "; ".join(
                f"{item.name}: {item.detail}"
                for item in failed
            )
            raise AssertionError(details)

    @staticmethod
    def _proposal(
        *,
        strategy: str = "property",
        current: float = 70.0,
        proposed: float = 100.0,
        observations: int = 5,
        confidence: float = 80.0,
    ) -> LearningChangeProposal:
        return LearningChangeProposal(
            strategy=strategy,
            current_score=current,
            proposed_score=proposed,
            observations=observations,
            improvement=proposed - current,
            improved=proposed > current,
            regression_detected=False,
            regression_severity="none",
            confidence=confidence,
            rationale="benchmark improvement",
        )

    def _case_approval_and_application(
        self,
    ) -> GovernedLearningBenchmarkResult:
        controller = LearningGovernanceController()

        result = controller.evaluate(
            self._proposal()
        )

        passed = (
            result.approved
            and result.applied
            and result.change is not None
            and result.change.applied_score == 100.0
        )

        return GovernedLearningBenchmarkResult(
            name="approval_and_application",
            passed=passed,
            detail=(
                "approved and applied"
                if passed
                else "approval/application failed"
            ),
        )

    def _case_rejected_change(
        self,
    ) -> GovernedLearningBenchmarkResult:
        controller = LearningGovernanceController()

        result = controller.evaluate(
            self._proposal(
                observations=2,
            )
        )

        passed = (
            not result.approved
            and not result.applied
            and result.change is None
            and controller.all_applied() == ()
        )

        return GovernedLearningBenchmarkResult(
            name="rejected_change",
            passed=passed,
            detail=(
                "rejected before application"
                if passed
                else "rejected change was applied"
            ),
        )

    def _case_history_persistence(
        self,
    ) -> GovernedLearningBenchmarkResult:
        store = ExperienceStore(":memory:")
        history = LearningChangeHistory(store)

        controller = LearningGovernanceController(
            history=history,
        )

        result = controller.evaluate(
            self._proposal()
        )

        records = history.recent()

        passed = (
            result.approved
            and result.applied
            and len(records) == 1
            and records[0].category == "learning_change"
            and records[0].success is True
        )

        return GovernedLearningBenchmarkResult(
            name="history_persistence",
            passed=passed,
            detail=(
                "approved change persisted"
                if passed
                else "history persistence failed"
            ),
        )

    def _case_automatic_rollback(
        self,
    ) -> GovernedLearningBenchmarkResult:
        application = LearningChangeApplication()
        controller = LearningGovernanceController(
            application=application,
        )

        first = controller.evaluate(
            self._proposal(
                current=70.0,
                proposed=90.0,
            )
        )

        second = controller.evaluate(
            self._proposal(
                current=90.0,
                proposed=100.0,
                confidence=90.0,
            )
        )

        rollback = AutomaticLearningRollback(
            application=application,
        )

        result = rollback.evaluate(
            strategy="property",
            baseline_score=100.0,
            learned_score=40.0,
        )

        restored_score = (
            result.restored.applied_score
            if result.restored is not None
            else None
        )

        passed = (
            first.applied
            and second.applied
            and result.rollback_requested
            and result.rolled_back
            and restored_score == 90.0
            and application.get("property") is not None
            and application.get("property").applied_score == 90.0
        )

        return GovernedLearningBenchmarkResult(
            name="automatic_rollback",
            passed=passed,
            detail=(
                "previous state restored"
                if passed
                else "rollback did not restore previous state"
            ),
        )

    def _case_first_change_rollback(
        self,
    ) -> GovernedLearningBenchmarkResult:
        application = LearningChangeApplication()
        controller = LearningGovernanceController(
            application=application,
        )

        applied = controller.evaluate(
            self._proposal()
        )

        rollback = AutomaticLearningRollback(
            application=application,
        )

        result = rollback.evaluate(
            strategy="property",
            baseline_score=100.0,
            learned_score=30.0,
        )

        passed = (
            applied.applied
            and result.rollback_requested
            and result.rolled_back
            and result.restored is None
            and application.get("property") is None
        )

        return GovernedLearningBenchmarkResult(
            name="first_change_rollback",
            passed=passed,
            detail=(
                "first applied state removed safely"
                if passed
                else "first-change rollback failed"
            ),
        )
