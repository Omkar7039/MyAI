from __future__ import annotations

from dataclasses import dataclass

from experience.applicability import ExperienceApplicabilityFilter
from experience.conflict import ExperienceConflictDetector
from experience.retriever import ExperienceRetriever


@dataclass(frozen=True)
class ExperienceGuidance:
    task: str
    successful: list
    warnings: list
    text: str


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

                block = (
                    f"- {exp.task}\n"
                    f"  Action: {exp.action}\n"
                    f"  Outcome: {exp.outcome}\n"
                    f"  Lesson: {exp.lesson}\n"
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

        sections.append(
            "\nUse historical guidance only as a hint. "
            "Do not copy an old solution blindly."
        )

        text = "\n".join(sections)

        return ExperienceGuidance(
            task=task,
            successful=successful,
            warnings=warnings,
            text=text[:self.max_chars],
        )
