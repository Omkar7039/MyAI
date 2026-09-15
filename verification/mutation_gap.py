from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class MutationGapAssessment:
    total_mutations: int
    killed_mutations: int
    survived_mutations: int
    invalid_mutations: int
    kill_rate: float
    gap_rate: float
    strong: bool
    reasons: tuple[str, ...]

    @property
    def mutation_gap(self) -> int:
        return self.survived_mutations


class MutationGapAnalyzer:
    """
    Analyze mutation-test outcomes.

    Each mutation outcome may be:
      - a bool: True means killed, False means survived
      - a mapping containing a `killed` field
      - an object containing a `killed` attribute
      - a mapping/object containing `status`

    Recognized killed statuses:
      killed, fail, failed, detected

    Recognized survived statuses:
      survived, pass, passed, undetected
    """

    KILLED_STATUSES = {
        "killed",
        "kill",
        "fail",
        "failed",
        "detected",
    }

    SURVIVED_STATUSES = {
        "survived",
        "survive",
        "pass",
        "passed",
        "undetected",
    }

    def assess(
        self,
        mutation_results: Iterable[Any],
    ) -> MutationGapAssessment:
        total = 0
        killed = 0
        survived = 0
        invalid = 0

        for result in mutation_results:
            total += 1

            outcome = self._classify(result)

            if outcome == "killed":
                killed += 1
            elif outcome == "survived":
                survived += 1
            else:
                invalid += 1

        kill_rate = (killed / total) * 100.0 if total else 0.0
        gap_rate = (survived / total) * 100.0 if total else 0.0

        reasons: list[str] = []

        if total == 0:
            reasons.append("no mutation outcomes were provided")
        else:
            if survived:
                reasons.append("some mutations survived the current tests")
            else:
                reasons.append("all valid mutations were killed")

            if invalid:
                reasons.append("some mutation outcomes were invalid or unknown")

            if kill_rate >= 80.0 and invalid == 0:
                reasons.append("mutation detection is strong")
            elif kill_rate >= 60.0:
                reasons.append("mutation detection is moderate")
            else:
                reasons.append("mutation detection is weak")

        strong = (
            total > 0
            and invalid == 0
            and survived == 0
            and kill_rate >= 80.0
        )

        return MutationGapAssessment(
            total_mutations=total,
            killed_mutations=killed,
            survived_mutations=survived,
            invalid_mutations=invalid,
            kill_rate=kill_rate,
            gap_rate=gap_rate,
            strong=strong,
            reasons=tuple(reasons),
        )

    @classmethod
    def _classify(cls, result: Any) -> str:
        if isinstance(result, bool):
            return "killed" if result else "survived"

        value = cls._extract_value(result, "killed")
        if isinstance(value, bool):
            return "killed" if value else "survived"

        status = cls._extract_value(result, "status")
        if isinstance(status, str):
            normalized = status.strip().lower()
            if normalized in cls.KILLED_STATUSES:
                return "killed"
            if normalized in cls.SURVIVED_STATUSES:
                return "survived"

        return "invalid"

    @staticmethod
    def _extract_value(result: Any, name: str) -> Any:
        if isinstance(result, dict):
            return result.get(name)

        return getattr(result, name, None)
