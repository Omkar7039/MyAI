from __future__ import annotations

from dataclasses import dataclass

from experience.retriever import RetrievedExperience


@dataclass(frozen=True)
class ExperienceApplicability:
    applicable: bool
    score: float
    reason: str


class ExperienceApplicabilityFilter:
    """
    Determine whether a retrieved historical experience is applicable
    to the current task.

    Historical experience is advisory only. Current source, requirements,
    and verification remain authoritative.
    """

    MIN_SCORE = 35.0

    def evaluate(
        self,
        query: str,
        result: RetrievedExperience,
    ) -> ExperienceApplicability:
        query_tokens = self._tokens(query)

        experience = result.experience

        task_tokens = self._tokens(experience.task)
        action_tokens = self._tokens(experience.action)
        outcome_tokens = self._tokens(experience.outcome)
        lesson_tokens = self._tokens(experience.lesson)

        task_overlap = query_tokens.intersection(task_tokens)
        context_overlap = query_tokens.intersection(
            action_tokens
            | outcome_tokens
            | lesson_tokens
        )

        score = 0.0

        if task_overlap:
            score += min(
                50.0,
                len(task_overlap) * 20.0,
            )

        if context_overlap:
            score += min(
                30.0,
                len(context_overlap) * 5.0,
            )

        if experience.success:
            score += 10.0

        if result.score >= 50.0:
            score += 10.0

        score = min(score, 100.0)

        if score >= self.MIN_SCORE:
            reason = "Historical experience is sufficiently related to the current task."
            applicable = True
        else:
            reason = "Historical experience is too weakly related to the current task."
            applicable = False

        return ExperienceApplicability(
            applicable=applicable,
            score=score,
            reason=reason,
        )

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {
            token
            for token in text.lower().split()
            if len(token) >= 2
        }
