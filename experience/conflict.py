from __future__ import annotations

from dataclasses import dataclass

from experience.retriever import RetrievedExperience


@dataclass(frozen=True)
class ExperienceConflict:
    detected: bool
    successful: list[RetrievedExperience]
    warnings: list[RetrievedExperience]
    text: str


class ExperienceConflictDetector:
    """Detect disagreement between relevant historical experiences."""

    def detect(
        self,
        successful: list[RetrievedExperience],
        warnings: list[RetrievedExperience],
    ) -> ExperienceConflict:
        if not successful or not warnings:
            return ExperienceConflict(
                detected=False,
                successful=successful,
                warnings=warnings,
                text="",
            )

        text = (
            "CONFLICTING HISTORICAL EXPERIENCE:\n"
            "Historical precedents disagree.\n"
            "Successful and failed outcomes both exist for related tasks.\n"
            "Treat historical evidence as inconclusive.\n"
            "Current source code, requirements, and verification results "
            "remain authoritative.\n"
        )

        return ExperienceConflict(
            detected=True,
            successful=successful,
            warnings=warnings,
            text=text,
        )
