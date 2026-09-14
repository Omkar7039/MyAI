from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExperienceQuality:
    accepted: bool
    score: float
    reason: str


class ExperienceQualityChecker:
    """
    Validate whether an experience is useful enough to persist.

    This does not decide whether the underlying repair was correct.
    Verification remains authoritative outside this component.
    """

    MIN_TEXT_LENGTH = 8

    def evaluate(
        self,
        task: str,
        action: str,
        outcome: str,
        lesson: str,
        success: bool,
    ) -> ExperienceQuality:
        fields = {
            "task": (task or "").strip(),
            "action": (action or "").strip(),
            "outcome": (outcome or "").strip(),
            "lesson": (lesson or "").strip(),
        }

        missing = [
            name
            for name, value in fields.items()
            if len(value) < self.MIN_TEXT_LENGTH
        ]

        if missing:
            return ExperienceQuality(
                accepted=False,
                score=0.0,
                reason=(
                    "Insufficient experience detail: "
                    + ", ".join(missing)
                ),
            )
        score = 0.0

        # Each required field contributes to the base quality.
        score += 20.0 * len(fields)

        # More specific descriptions are more useful later.
        for value in fields.values():
            if len(value) >= 40:
                score += 5.0

        # Successful verified experiences are stronger precedents.
        if success:
            score += 10.0

        accepted = score >= 70.0

        return ExperienceQuality(
            accepted=accepted,
            score=min(score, 100.0),
            reason=(
                "Experience contains sufficient actionable detail."
                if accepted
                else "Experience detail is too weak for durable memory."
            ),
        )
