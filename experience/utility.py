from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExperienceUtility:
    score: float
    useful: bool
    baseline_score: float
    observed_score: float
    improvement: float
    reasons: tuple[str, ...]


class ExperienceUtilityMeasurer:
    """
    Measure whether an experience improved an observed outcome.

    The measurement is intentionally independent from retrieval and
    persistence. A historical experience is useful only when the
    observed outcome improves relative to the baseline.
    """

    def measure(
        self,
        *,
        baseline_score: float,
        observed_score: float,
        applied: bool = True,
    ) -> ExperienceUtility:
        self._validate_score(baseline_score, "baseline_score")
        self._validate_score(observed_score, "observed_score")

        improvement = observed_score - baseline_score
        reasons: list[str] = []

        if not applied:
            return ExperienceUtility(
                score=0.0,
                useful=False,
                baseline_score=baseline_score,
                observed_score=observed_score,
                improvement=0.0,
                reasons=("experience was not applied",),
            )

        if improvement > 0.0:
            score = min(100.0, improvement * 2.0)
            useful = True
            reasons.append("experience improved the observed outcome")
        elif improvement == 0.0:
            score = 0.0
            useful = False
            reasons.append("experience produced no measurable improvement")
        else:
            score = 0.0
            useful = False
            reasons.append("experience reduced the observed outcome")

        return ExperienceUtility(
            score=score,
            useful=useful,
            baseline_score=baseline_score,
            observed_score=observed_score,
            improvement=improvement,
            reasons=tuple(reasons),
        )

    @staticmethod
    def _validate_score(value: float, name: str) -> None:
        if not 0.0 <= value <= 100.0:
            raise ValueError(
                f"{name} must be between 0 and 100"
            )
