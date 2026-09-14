from __future__ import annotations

from dataclasses import dataclass, field

from experience.applicability import ExperienceApplicabilityFilter
from experience.confidence import ExperienceConfidenceCalculator
from experience.consolidator import ExperienceConsolidation, ExperienceConsolidator
from experience.consolidator import ExperienceConsolidation, ExperienceConsolidator
from experience.contradiction import ExperienceContradiction, ExperienceContradictionResolver
from experience.conflict import ExperienceConflictDetector
from experience.freshness import ExperienceFreshnessCalculator
from experience.retriever import ExperienceRetriever


@dataclass(frozen=True)
class ExperienceGuidance:
    task: str
    successful: list
    warnings: list
    text: str
    confidences: list = field(default_factory=list)
    contradiction: ExperienceContradiction | None = None
    consolidation: ExperienceConsolidation | None = None
    consolidation: ExperienceConsolidation | None = None


class ExperiencePlanner:
    """
    Build advisory guidance from historical experiences.

    Current source code and current verification always have priority.
    """

    def __init__(
        self,
        retriever: ExperienceRetriever | None = None,
        max_chars: int = 1600,
    ):
        if max_chars < 1:
            raise ValueError("max_chars must be >= 1")

        self.retriever = retriever or ExperienceRetriever()
        self.max_chars = max_chars
        self.applicability_filter = ExperienceApplicabilityFilter()
        self.conflict_detector = ExperienceConflictDetector()
        self.contradiction_resolver = ExperienceContradictionResolver()
        self.consolidator = ExperienceConsolidator()
        self.consolidator = ExperienceConsolidator()
        self.confidence_calculator = ExperienceConfidenceCalculator()
        self.freshness_calculator = ExperienceFreshnessCalculator()

    def plan(self, task: str) -> ExperienceGuidance:
        if not task or not task.strip():
            return ExperienceGuidance(
                task=task,
                successful=[],
                warnings=[],
                text="",
            )

        retrieved_successful = self.retriever.successful(
            task,
            limit=3,
        )

        retrieved_warnings = self.retriever.warnings(
            task,
            limit=3,
        )

        successful = [
            item
            for item in retrieved_successful
            if self.applicability_filter.evaluate(
                task,
                item,
            ).applicable
        ]

        warnings = [
            item
            for item in retrieved_warnings
            if self.applicability_filter.evaluate(
                task,
                item,
            ).applicable
        ]

        conflict = self.conflict_detector.detect(
            successful,
            warnings,
        )

        contradiction = self.contradiction_resolver.resolve(
            successful,
            warnings,
        )

        consolidation = self.consolidator.consolidate(
            successful + warnings,
            max_chars=min(900, self.max_chars),
        )

        confidences = []

        for item in successful + warnings:
            applicability = self.applicability_filter.evaluate(
                task,
                item,
            )

            freshness = self.freshness_calculator.calculate(
                item.experience,
            )

            confidence = self.confidence_calculator.calculate(
                item,
                applicability,
                freshness,
                conflict=conflict,
            )

            confidences.append(
                (item.experience.experience_id, confidence)
            )

        confidence_by_id = dict(confidences)

        sections = [
            "HISTORICAL EXPERIENCE GUIDANCE:",
            "This is advisory context only.",
            "Current source code, requirements, and verification "
            "results are authoritative.",
        ]

        used = sum(len(x) for x in sections)

        if successful:
            sections.append("\nSUCCESSFUL PRECEDENTS:")

            for item in successful:
                exp = item.experience

                confidence = confidence_by_id.get(
                    exp.experience_id
                )

                confidence_line = (
                    f"  Confidence: {confidence.label} ({confidence.score:.1f})\n"
                    if confidence is not None
                    else ""
                )

                block = (
                    f"- {exp.task}\n"
                    + confidence_line
                    + f"  Action: {exp.action}\n"
                    + f"  Outcome: {exp.outcome}\n"
                    + f"  Lesson: {exp.lesson}\n"
                )

                if used + len(block) > self.max_chars:
                    break

                sections.append(block)
                used += len(block)
        else:
            sections.append(
                "\nNo successful precedent was found."
            )

        if warnings and used < self.max_chars:
            sections.append("\nFAILED ATTEMPTS / WARNINGS:")

            for item in warnings:
                exp = item.experience

                confidence = confidence_by_id.get(
                    exp.experience_id
                )

                confidence_line = (
                    f"  Confidence: {confidence.label} ({confidence.score:.1f})\n"
                    if confidence is not None
                    else ""
                )

                block = (
                    f"- {exp.task}\n"
                    f"  Previous action: {exp.action}\n"
                    f"  Outcome: {exp.outcome}\n"
                    f"  Warning: {exp.lesson}\n"
                )

                if used + len(block) > self.max_chars:
                    break

                sections.append(block)
                used += len(block)

        if conflict.detected and used < self.max_chars:
            conflict_block = "\n" + conflict.text

            if used + len(conflict_block) <= self.max_chars:
                sections.append(conflict_block)
                used += len(conflict_block)

        if consolidation.experience_ids and used < self.max_chars:
            consolidation_block = "\n" + consolidation.summary

            if used + len(consolidation_block) <= self.max_chars:
                sections.append(consolidation_block)
                used += len(consolidation_block)

        if contradiction.detected and used < self.max_chars:
            contradiction_block = (
                "\nHISTORICAL CONTRADICTION ANALYSIS:\n"
                + contradiction.recommendation
            )

            if contradiction.dimensions:
                contradiction_block += (
                    "\nDimensions: "
                    + ", ".join(contradiction.dimensions)
                )

            if used + len(contradiction_block) <= self.max_chars:
                sections.append(contradiction_block)
                used += len(contradiction_block)

        if consolidation.experience_ids and used < self.max_chars:
            consolidation_block = "\n" + consolidation.summary

            if used + len(consolidation_block) <= self.max_chars:
                sections.append(consolidation_block)
                used += len(consolidation_block)

        sections.append(
            "\nUse historical guidance only as a hint. "
            "Do not copy an old solution blindly."
        )

        text = "\n".join(sections)

        return ExperienceGuidance(
            task=task,
            successful=successful,
            warnings=warnings,
            confidences=confidences,
            contradiction=contradiction,
            consolidation=consolidation,
            text=text[:self.max_chars],
        )
