from __future__ import annotations

from dataclasses import dataclass

from experience.adaptive_strategy import AdaptiveStrategyScore


@dataclass(frozen=True)
class LearningPolicyDecision:
    allowed: bool
    strategy: str | None
    confidence: float
    reason: str


class LearningPolicy:
    """
    Decide whether historical strategy performance is strong enough
    to influence a future strategy choice.

    Safeguards:
      - minimum observations
      - minimum success rate
      - minimum adaptive score
      - configurable confidence threshold

    The policy never forces a strategy when evidence is insufficient.
    """

    def __init__(
        self,
        *,
        min_observations: int = 3,
        min_success_rate: float = 70.0,
        min_score: float = 70.0,
    ):
        if min_observations < 1:
            raise ValueError("min_observations must be at least 1")

        if not 0.0 <= min_success_rate <= 100.0:
            raise ValueError(
                "min_success_rate must be between 0 and 100"
            )

        if not 0.0 <= min_score <= 100.0:
            raise ValueError(
                "min_score must be between 0 and 100"
            )

        self.min_observations = min_observations
        self.min_success_rate = min_success_rate
        self.min_score = min_score

    def decide(
        self,
        candidate: AdaptiveStrategyScore | None,
    ) -> LearningPolicyDecision:
        if candidate is None:
            return LearningPolicyDecision(
                allowed=False,
                strategy=None,
                confidence=0.0,
                reason="no historical strategy evidence",
            )

        if candidate.total_outcomes < self.min_observations:
            return LearningPolicyDecision(
                allowed=False,
                strategy=candidate.strategy,
                confidence=self._confidence(candidate),
                reason=(
                    "insufficient historical observations"
                ),
            )

        if candidate.success_rate < self.min_success_rate:
            return LearningPolicyDecision(
                allowed=False,
                strategy=candidate.strategy,
                confidence=self._confidence(candidate),
                reason=(
                    "historical success rate is below policy threshold"
                ),
            )

        if candidate.score < self.min_score:
            return LearningPolicyDecision(
                allowed=False,
                strategy=candidate.strategy,
                confidence=self._confidence(candidate),
                reason=(
                    "adaptive strategy score is below policy threshold"
                ),
            )

        return LearningPolicyDecision(
            allowed=True,
            strategy=candidate.strategy,
            confidence=self._confidence(candidate),
            reason="historical evidence is sufficient",
        )

    @staticmethod
    def _confidence(
        candidate: AdaptiveStrategyScore,
    ) -> float:
        observation_factor = min(
            candidate.total_outcomes / 10.0,
            1.0,
        )

        score_factor = candidate.score / 100.0
        success_factor = candidate.success_rate / 100.0

        confidence = (
            observation_factor
            * score_factor
            * success_factor
            * 100.0
        )

        return max(0.0, min(100.0, confidence))
