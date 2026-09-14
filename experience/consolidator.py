from __future__ import annotations

from dataclasses import dataclass

from experience.retriever import RetrievedExperience


@dataclass(frozen=True)
class ExperienceConsolidation:
    task: str
    experience_ids: tuple[str, ...]
    summary: str


class ExperienceConsolidator:
    """Consolidate related historical experiences into compact guidance."""

    def consolidate(
        self,
        experiences: list[RetrievedExperience],
        max_chars: int = 1200,
    ) -> ExperienceConsolidation:
        if max_chars < 1:
            raise ValueError("max_chars must be >= 1")

        if not experiences:
            return ExperienceConsolidation(
                task="",
                experience_ids=(),
                summary="No experiences available for consolidation.",
            )

        task = experiences[0].experience.task.strip()
        experience_ids = tuple(
            item.experience.experience_id
            for item in experiences
        )

        successes = [
            item.experience
            for item in experiences
            if item.experience.success
        ]

        failures = [
            item.experience
            for item in experiences
            if not item.experience.success
        ]

        lines = [
            "CONSOLIDATED HISTORICAL EXPERIENCE:",
            f"Task: {task}",
            f"Records: {len(experiences)}",
        ]

        if successes:
            lines.append("Successful approaches:")
            for item in successes:
                lines.append(f"- {item.action}")

        if failures:
            lines.append("Warnings from failed attempts:")
            for item in failures:
                lines.append(f"- {item.lesson}")

        lines.append(
            "Use this consolidated history only as advisory context; "
            "current source code and verification remain authoritative."
        )

        summary = "\n".join(lines)

        return ExperienceConsolidation(
            task=task,
            experience_ids=experience_ids,
            summary=summary[:max_chars],
        )
