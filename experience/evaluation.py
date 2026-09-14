from __future__ import annotations

from dataclasses import dataclass

from experience.applicability import ExperienceApplicabilityFilter
from experience.confidence import ExperienceConfidenceCalculator
from experience.conflict import ExperienceConflictDetector
from experience.consolidator import ExperienceConsolidator
from experience.contradiction import ExperienceContradictionResolver
from experience.freshness import ExperienceFreshnessCalculator
from experience.provenance import ExperienceProvenance
from experience.retriever import RetrievedExperience
from experience.store import Experience


@dataclass(frozen=True)
class ExperienceEvaluationCase:
    name: str
    query: str
    experience: Experience
    expected_applicable: bool
    expected_confidence: str
    expected_freshness: str


@dataclass(frozen=True)
class ExperienceEvaluationResult:
    total_cases: int
    passed_cases: int
    failed_cases: int
    accuracy: float
    details: tuple[str, ...]


class ExperienceEvaluator:
    """Deterministically evaluate core experience-memory behavior."""

    def __init__(self):
        self.applicability = ExperienceApplicabilityFilter()
        self.confidence = ExperienceConfidenceCalculator()
        self.conflict = ExperienceConflictDetector()
        self.contradiction = ExperienceContradictionResolver()
        self.freshness = ExperienceFreshnessCalculator()
        self.consolidator = ExperienceConsolidator()

    def evaluate(
        self,
        cases: list[ExperienceEvaluationCase],
    ) -> ExperienceEvaluationResult:
        details = []
        passed = 0

        for case in cases:
            result = RetrievedExperience(
                experience=case.experience,
                score=70.0,
            )

            applicability = self.applicability.evaluate(
                case.query,
                result,
            )

            freshness = self.freshness.calculate(
                case.experience,
            )

            confidence = self.confidence.calculate(
                result,
                applicability,
                freshness,
            )

            checks = [
                applicability.applicable == case.expected_applicable,
                confidence.label == case.expected_confidence,
                freshness.label == case.expected_freshness,
            ]

            if all(checks):
                passed += 1
                details.append(
                    f"{case.name}: PASS"
                )
            else:
                details.append(
                    f"{case.name}: FAIL "
                    f"(applicable={applicability.applicable}, "
                    f"confidence={confidence.label}, "
                    f"freshness={freshness.label})"
                )

        total = len(cases)
        accuracy = (
            passed / total
            if total
            else 1.0
        )

        return ExperienceEvaluationResult(
            total_cases=total,
            passed_cases=passed,
            failed_cases=total - passed,
            accuracy=accuracy,
            details=tuple(details),
        )

    def evaluate_contradiction(
        self,
        successful: list[RetrievedExperience],
        warnings: list[RetrievedExperience],
    ):
        return self.contradiction.resolve(
            successful,
            warnings,
        )

    def evaluate_consolidation(
        self,
        experiences: list[RetrievedExperience],
        max_chars: int = 1200,
    ):
        return self.consolidator.consolidate(
            experiences,
            max_chars=max_chars,
        )
