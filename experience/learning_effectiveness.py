from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LearningEffectiveness:
    baseline_score: float
    learned_score: float
    improvement: float
    improved: bool
    regression: bool
    neutral: bool
    confidence: float
    reasons: tuple[str, ...]


class LearningEffectivenessEvaluator:
    """
    Compare a learned strategy outcome against the safe baseline.

    The learned strategy is considered:
      improved  -> learned score > baseline score
      regression -> learned score < baseline score
      neutral   -> learned score == baseline score

    Confidence reflects the magnitude of the observed difference.
    """

    def evaluate(
        self,
        *,
        baseline_score: float,
        learned_score: float,
    ) -> LearningEffectiveness:
        self._validate(
            baseline_score,
            "baseline_score",
        )
        self._validate(
            learned_score,
            "learned_score",
        )

        improvement = learned_score - baseline_score

        improved = improvement > 0.0
        regression = improvement < 0.0
        neutral = improvement == 0.0

        confidence = min(
            100.0,
            abs(improvement) * 2.0,
        )

        if improved:
            reasons = (
                "learned strategy outperformed the baseline",
            )
        elif regression:
            reasons = (
                "learned strategy underperformed the baseline",
            )
        else:
            reasons = (
                "learned strategy matched the baseline",
            )

        return LearningEffectiveness(
            baseline_score=baseline_score,
            learned_score=learned_score,
            improvement=improvement,
            improved=improved,
            regression=regression,
            neutral=neutral,
            confidence=confidence,
            reasons=reasons,
        )

    @staticmethod
    def _validate(
        value: float,
        name: str,
    ) -> None:
        if not 0.0 <= value <= 100.0:
            raise ValueError(
                f"{name} must be between 0 and 100"
            )
