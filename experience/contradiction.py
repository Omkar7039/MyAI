from __future__ import annotations

from dataclasses import dataclass

from experience.retriever import RetrievedExperience


@dataclass(frozen=True)
class ExperienceContradiction:
    detected: bool
    dimensions: tuple[str, ...]
    recommendation: str


class ExperienceContradictionResolver:
    """Identify and describe disagreement across historical experiences."""

    def resolve(
        self,
        successful: list[RetrievedExperience],
        warnings: list[RetrievedExperience],
    ) -> ExperienceContradiction:
        if not successful or not warnings:
            return ExperienceContradiction(
                detected=False,
                dimensions=(),
                recommendation="No historical contradiction was detected.",
            )

        dimensions: list[str] = []

        success_actions = {
            item.experience.action.strip().lower()
            for item in successful
        }
        warning_actions = {
            item.experience.action.strip().lower()
            for item in warnings
        }

        if success_actions != warning_actions:
            dimensions.append("action")

        success_outcomes = {
            item.experience.outcome.strip().lower()
            for item in successful
        }
        warning_outcomes = {
            item.experience.outcome.strip().lower()
            for item in warnings
        }

        if success_outcomes != warning_outcomes:
            dimensions.append("outcome")

        success_lessons = {
            item.experience.lesson.strip().lower()
            for item in successful
        }
        warning_lessons = {
            item.experience.lesson.strip().lower()
            for item in warnings
        }

        if success_lessons != warning_lessons:
            dimensions.append("lesson")

        if dimensions:
            recommendation = (
                "Historical evidence disagrees on: "
                + ", ".join(dimensions)
                + ". Require fresh verification from the current source and tests."
            )
        else:
            recommendation = (
                "Historical outcomes conflict. Require fresh verification "
                "from the current source and tests."
            )

        return ExperienceContradiction(
            detected=True,
            dimensions=tuple(dimensions),
            recommendation=recommendation,
        )
