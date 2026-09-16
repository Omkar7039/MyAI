from __future__ import annotations

from dataclasses import dataclass

from experience.learning_change_proposal import LearningChangeProposal
from experience.learning_governance import LearningGovernanceController


@dataclass(frozen=True)
class GovernanceBenchmarkCase:
    name: str
    proposal: LearningChangeProposal
    expected_approved: bool
    expected_applied: bool


@dataclass(frozen=True)
class GovernanceBenchmarkResult:
    name: str
    passed: bool
    approved: bool
    applied: bool


class LearningGovernanceBenchmark:
    def __init__(
        self,
        controller: LearningGovernanceController | None = None,
    ):
        self.controller = controller or LearningGovernanceController()

    @staticmethod
    def cases() -> tuple[GovernanceBenchmarkCase, ...]:
        return (
            GovernanceBenchmarkCase(
                name="strong improvement",
                proposal=LearningChangeProposal(
                    strategy="property",
                    current_score=70.0,
                    proposed_score=90.0,
                    observations=5,
                    improvement=20.0,
                    improved=True,
                    regression_detected=False,
                    regression_severity="none",
                    confidence=80.0,
                    rationale="strong improvement",
                ),
                expected_approved=True,
                expected_applied=True,
            ),
            GovernanceBenchmarkCase(
                name="insufficient observations",
                proposal=LearningChangeProposal(
                    strategy="mutation",
                    current_score=70.0,
                    proposed_score=90.0,
                    observations=2,
                    improvement=20.0,
                    improved=True,
                    regression_detected=False,
                    regression_severity="none",
                    confidence=80.0,
                    rationale="insufficient observations",
                ),
                expected_approved=False,
                expected_applied=False,
            ),
            GovernanceBenchmarkCase(
                name="neutral outcome",
                proposal=LearningChangeProposal(
                    strategy="standard",
                    current_score=80.0,
                    proposed_score=80.0,
                    observations=5,
                    improvement=0.0,
                    improved=False,
                    regression_detected=False,
                    regression_severity="none",
                    confidence=80.0,
                    rationale="neutral",
                ),
                expected_approved=False,
                expected_applied=False,
            ),
            GovernanceBenchmarkCase(
                name="low confidence",
                proposal=LearningChangeProposal(
                    strategy="multifile",
                    current_score=70.0,
                    proposed_score=90.0,
                    observations=5,
                    improvement=20.0,
                    improved=True,
                    regression_detected=False,
                    regression_severity="none",
                    confidence=20.0,
                    rationale="low confidence",
                ),
                expected_approved=False,
                expected_applied=False,
            ),
            GovernanceBenchmarkCase(
                name="regression",
                proposal=LearningChangeProposal(
                    strategy="rollback-candidate",
                    current_score=90.0,
                    proposed_score=40.0,
                    observations=5,
                    improvement=-50.0,
                    improved=False,
                    regression_detected=True,
                    regression_severity="high",
                    confidence=100.0,
                    rationale="regression",
                ),
                expected_approved=False,
                expected_applied=False,
            ),
        )

    def run(self) -> tuple[GovernanceBenchmarkResult, ...]:
        results: list[GovernanceBenchmarkResult] = []

        for case in self.cases():
            decision = self.controller.evaluate(case.proposal)

            passed = (
                decision.approved == case.expected_approved
                and decision.applied == case.expected_applied
            )

            results.append(
                GovernanceBenchmarkResult(
                    name=case.name,
                    passed=passed,
                    approved=decision.approved,
                    applied=decision.applied,
                )
            )

        return tuple(results)

    def all_passed(self) -> bool:
        return all(result.passed for result in self.run())
