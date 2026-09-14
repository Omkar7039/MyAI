from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from experience.store import Experience


@dataclass(frozen=True)
class ExperienceFreshness:
    age_days: float
    score: float
    label: str


class ExperienceFreshnessCalculator:
    """Calculate deterministic freshness for historical experience."""

    HALF_LIFE_DAYS = 180.0

    def calculate(
        self,
        experience: Experience,
        now: datetime | None = None,
    ) -> ExperienceFreshness:
        current = now or datetime.now(timezone.utc)

        if hasattr(experience, "experience"):
            experience = experience.experience

        created_at = experience.created_at

        if not created_at:
            return ExperienceFreshness(
                age_days=0.0,
                score=1.0,
                label="unknown-age",
            )

        timestamp = datetime.fromisoformat(
            created_at.replace("Z", "+00:00")
        )

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        age_seconds = max(
            0.0,
            (current - timestamp).total_seconds(),
        )
        age_days = age_seconds / 86400.0

        score = 2.0 ** (
            -age_days / self.HALF_LIFE_DAYS
        )

        if age_days <= 30:
            label = "fresh"
        elif age_days <= 180:
            label = "aging"
        else:
            label = "old"

        return ExperienceFreshness(
            age_days=age_days,
            score=score,
            label=label,
        )
