from __future__ import annotations

from dataclasses import dataclass

from experience.applicability import ExperienceApplicability
from experience.conflict import ExperienceConflict
from experience.freshness import ExperienceFreshness
from experience.retriever import RetrievedExperience


@dataclass(frozen=True)
class ExperienceConfidence:
    score: float
    label: str
    reasons: tuple[str, ...]


class ExperienceConfidenceCalculator:
    """Calculate bounded advisory confidence for historical experience."""

    def calculate(
        self,
        result: RetrievedExperience,
        applicability: ExperienceApplicability,
        freshness: ExperienceFreshness,
        conflict: ExperienceConflict | None = None,
    ) -> ExperienceConfidence:
        score = 0.0
        reasons: list[str] = []

        # Retrieval relevance contributes up to 40 points.
        score += min(
            40.0,
            max(0.0, result.score),
        )

        # Applicability contributes up to 30 points.
        score += min(
            30.0,
            max(0.0, applicability.score) * 0.30,
        )

        # Freshness contributes up to 15 points.
        score += min(
            15.0,
            max(0.0, freshness.score) * 15.0,
        )

        experience = result.experience

        if experience.success:
            score += 10.0
            reasons.append("Historical repair succeeded.")
        else:
            score -= 10.0
            reasons.append("Historical repair failed; treat it as a warning.")

        if result.score >= 50.0:
            reasons.append("Retrieval relevance is strong.")

        if applicability.applicable:
            reasons.append("Experience is applicable to the current task.")

        if freshness.label == "fresh":
            reasons.append("Experience is recent.")
        elif freshness.label == "old":
            reasons.append("Experience is old and should be re-verified.")

        if conflict is not None and conflict.detected:
            score -= 25.0
            reasons.append("Conflicting historical outcomes reduce confidence.")

        score = max(0.0, min(100.0, score))

        if score >= 80.0:
            label = "high"
        elif score >= 55.0:
            label = "medium"
        else:
            label = "low"

        return ExperienceConfidence(
            score=score,
            label=label,
            reasons=tuple(reasons),
        )
