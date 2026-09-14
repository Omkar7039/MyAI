from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExperienceFeedback:
    score: float
    accepted: bool
    strengths: list[str]
    gaps: list[str]
    improved_lesson: str


class ExperienceFeedbackEngine:
    """
    Deterministic post-recording feedback for repair experiences.

    This layer does not replace current-source verification.
    It only improves the durability and usefulness of historical lessons.
    """

    MIN_SCORE = 75.0

    def evaluate(
        self,
        *,
        task: str,
        action: str,
        outcome: str,
        success: bool,
        lesson: str,
        metadata: str = "",
    ) -> ExperienceFeedback:
        fields = {
            "task": task.strip(),
            "action": action.strip(),
            "outcome": outcome.strip(),
            "lesson": lesson.strip(),
        }

        strengths: list[str] = []
        gaps: list[str] = []

        score = 0.0

        for name, value in fields.items():
            if value:
                score += 15.0
            else:
                gaps.append(f"Missing {name} detail.")

        if len(fields["task"]) >= 40:
            score += 5.0
            strengths.append("Task is specific.")
        elif fields["task"]:
            gaps.append("Task could describe the defect more precisely.")

        if len(fields["action"]) >= 40:
            score += 5.0
            strengths.append("Action contains useful implementation detail.")
        elif fields["action"]:
            gaps.append("Action is too generic.")

        if len(fields["outcome"]) >= 40:
            score += 5.0
            strengths.append("Outcome contains verification detail.")
        elif fields["outcome"]:
            gaps.append("Outcome should identify concrete verification evidence.")

        if len(fields["lesson"]) >= 40:
            score += 5.0
            strengths.append("Lesson is actionable.")
        elif fields["lesson"]:
            gaps.append("Lesson should explain what should be repeated or avoided.")

        if success:
            score += 10.0
            strengths.append("Experience came from a successful repair.")
        else:
            gaps.append("Failed experience should emphasize the warning or failure mode.")

        if metadata.strip():
            score += 5.0
            strengths.append("Metadata provides additional context.")

        score = min(score, 100.0)
        accepted = score >= self.MIN_SCORE

        if success:
            if accepted:
                improved_lesson = (
                    f"{lesson.strip()} "
                    "Preserve the verified approach, but re-check it against "
                    "the current source code and tests before reuse."
                )
            else:
                improved_lesson = (
                    f"{lesson.strip()} "
                    "Historical evidence is incomplete; verify the approach "
                    "against current source code and tests before reuse."
                )
        else:
            if lesson.strip():
                improved_lesson = (
                    f"{lesson.strip()} "
                    "Treat this experience as a warning and avoid repeating "
                    "the same approach without new evidence."
                )
            else:
                improved_lesson = (
                    "Previous repair attempt did not provide sufficient evidence. "
                    "Treat it as a warning and require fresh verification."
                )

        return ExperienceFeedback(
            score=score,
            accepted=accepted,
            strengths=strengths,
            gaps=gaps,
            improved_lesson=improved_lesson.strip(),
        )
