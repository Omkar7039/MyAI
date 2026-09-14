from __future__ import annotations

from dataclasses import dataclass

from experience.freshness import ExperienceFreshnessCalculator
from experience.store import Experience


@dataclass(frozen=True)
class ExperienceLifecycleDecision:
    experience_id: str
    action: str
    reason: str


class ExperienceLifecycleManager:
    """Classify historical experiences for retention or cleanup."""

    def __init__(
        self,
        freshness: ExperienceFreshnessCalculator | None = None,
        archive_after_days: float = 365.0,
        delete_after_days: float = 730.0,
    ):
        if archive_after_days < 0:
            raise ValueError("archive_after_days must be >= 0")
        if delete_after_days <= archive_after_days:
            raise ValueError(
                "delete_after_days must be greater than archive_after_days"
            )

        self.freshness = freshness or ExperienceFreshnessCalculator()
        self.archive_after_days = archive_after_days
        self.delete_after_days = delete_after_days

    def classify(
        self,
        experience: Experience,
        now=None,
    ) -> ExperienceLifecycleDecision:
        freshness = self.freshness.calculate(experience, now=now)

        if not experience.created_at:
            return ExperienceLifecycleDecision(
                experience_id=experience.experience_id,
                action="retain",
                reason="Missing age metadata; retain conservatively.",
            )

        if freshness.age_days >= self.delete_after_days:
            if experience.success:
                return ExperienceLifecycleDecision(
                    experience_id=experience.experience_id,
                    action="archive",
                    reason="Old successful experience; archive instead of deleting valuable history.",
                )

            return ExperienceLifecycleDecision(
                experience_id=experience.experience_id,
                action="delete",
                reason="Old failed experience exceeded deletion threshold.",
            )

        if freshness.age_days >= self.archive_after_days:
            return ExperienceLifecycleDecision(
                experience_id=experience.experience_id,
                action="archive",
                reason="Experience exceeded archive age threshold.",
            )

        return ExperienceLifecycleDecision(
            experience_id=experience.experience_id,
            action="retain",
            reason="Experience remains within retention window.",
        )
