from __future__ import annotations

import re
from dataclasses import dataclass

from experience.store import Experience, ExperienceStore


@dataclass(frozen=True)
class RetrievedExperience:
    experience: Experience
    score: float


class ExperienceRetriever:
    """
    Deterministic local retrieval for past MyAI experiences.

    Successful experiences are ranked as positive precedents.
    Failed experiences are ranked as warnings.
    """

    def __init__(
        self,
        store: ExperienceStore | None = None,
    ):
        self.store = store or ExperienceStore(
            "data/experience.db"
        )

    def search(
        self,
        query: str,
        limit: int = 10,
        include_failures: bool = True,
    ) -> list[RetrievedExperience]:
        if not query or not query.strip():
            return []

        if limit < 1:
            raise ValueError("limit must be >= 1")

        candidates = self.store.search(
            query,
            limit=max(limit * 3, 10),
        )

        if not include_failures:
            candidates = [
                item
                for item in candidates
                if item.success
            ]

        query_tokens = self._tokens(query)

        results = []

        for experience in candidates:
            score = self._score(
                query_tokens,
                experience,
            )

            if score > 0:
                results.append(
                    RetrievedExperience(
                        experience=experience,
                        score=score,
                    )
                )

        results.sort(
            key=lambda item: (
                -item.score,
                not item.experience.success,
                item.experience.experience_id,
            )
        )

        results = self._deduplicate(results)

        return results[:limit]

    def successful(
        self,
        query: str,
        limit: int = 5,
    ) -> list[RetrievedExperience]:
        return self.search(
            query=query,
            limit=limit,
            include_failures=False,
        )

    def warnings(
        self,
        query: str,
        limit: int = 5,
    ) -> list[RetrievedExperience]:
        results = self.search(
            query=query,
            limit=max(limit * 2, 10),
            include_failures=True,
        )

        results = [
            item
            for item in results
            if not item.experience.success
        ]

        return results[:limit]

    @staticmethod
    def _experience_key(experience: Experience) -> str:
        return "|".join(
            [
                experience.task.strip().lower(),
                experience.action.strip().lower(),
                experience.outcome.strip().lower(),
                str(experience.success),
                experience.lesson.strip().lower(),
            ]
        )

    @staticmethod
    def _deduplicate(
        results: list[RetrievedExperience],
    ) -> list[RetrievedExperience]:
        seen = set()
        output = []

        for result in results:
            key = ExperienceRetriever._experience_key(
                result.experience
            )

            if key in seen:
                continue

            seen.add(key)
            output.append(result)

        return output

    @staticmethod
    def _quality_bonus(experience: Experience) -> float:
        """Add a deterministic ranking bonus for durable experiences."""
        bonus = 0.0

        if experience.success:
            bonus += 10.0

        outcome = experience.outcome.lower()
        lesson = experience.lesson.lower()
        action = experience.action.lower()

        verification_terms = (
            "verified",
            "verification",
            "regression",
            "mutation",
            "property",
            "test",
            "tests passed",
        )

        evidence_hits = sum(
            1
            for term in verification_terms
            if term in outcome or term in lesson
        )

        bonus += min(evidence_hits * 4.0, 16.0)

        if len(action) >= 40:
            bonus += 3.0

        if len(lesson) >= 40:
            bonus += 3.0

        return bonus

    @staticmethod
    def _score(
        query_tokens: set[str],
        experience: Experience,
    ) -> float:
        fields = [
            experience.task,
            experience.category,
            experience.action,
            experience.outcome,
            experience.lesson,
        ]

        text = " ".join(fields).lower()
        content_tokens = ExperienceRetriever._tokens(text)

        matched = query_tokens.intersection(
            content_tokens
        )

        score = min(
            40.0,
            len(matched) * 8.0,
        )

        if experience.success:
            score += 5.0
        else:
            score += 2.0

        category_tokens = ExperienceRetriever._tokens(
            experience.category
        )

        if query_tokens.intersection(category_tokens):
            score += 10.0

        return score + ExperienceRetriever._quality_bonus(
            experience
        )

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {
            token
            for token in re.findall(
                r"[A-Za-z_][A-Za-z0-9_.]*",
                text.lower(),
            )
            if len(token) >= 2
        }
