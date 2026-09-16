from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LearningRegression:
    strategy: str
    baseline_score: float
    learned_score: float
    regression: float
    detected: bool
    severity: str
    reason: str


class LearningRegressionDetector:
    """
    Detect degradation of a learned strategy against its baseline.

    Severity:
      none     -> no regression
      low      -> regression > 0 and <= 10
      medium   -> regression > 10 and <= 25
      high     -> regression > 25

    A regression is measured as:

        baseline_score - learned_score
    """

    def __init__(
        self,
        *,
        low_threshold: float = 10.0,
        medium_threshold: float = 25.0,
    ):
        if low_threshold <= 0.0:
            raise ValueError(
                "low_threshold must be greater than 0"
            )

        if medium_threshold <= low_threshold:
            raise ValueError(
                "medium_threshold must be greater than low_threshold"
            )

        self.low_threshold = float(low_threshold)
        self.medium_threshold = float(medium_threshold)

    def detect(
        self,
        *,
        strategy: str,
        baseline_score: float,
        learned_score: float,
    ) -> LearningRegression:
        name = strategy.strip()

        if not name:
            raise ValueError("strategy must not be empty")

        self._validate(
            baseline_score,
            "baseline_score",
        )
        self._validate(
            learned_score,
            "learned_score",
        )

        regression = baseline_score - learned_score

        if regression <= 0.0:
            return LearningRegression(
                strategy=name,
                baseline_score=baseline_score,
                learned_score=learned_score,
                regression=regression,
                detected=False,
                severity="none",
                reason="learned strategy is not performing worse than baseline",
            )

        if regression <= self.low_threshold:
            severity = "low"
        elif regression <= self.medium_threshold:
            severity = "medium"
        else:
            severity = "high"

        return LearningRegression(
            strategy=name,
            baseline_score=baseline_score,
            learned_score=learned_score,
            regression=regression,
            detected=True,
            severity=severity,
            reason=(
                f"learned strategy regressed by "
                f"{regression:.2f} points"
            ),
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
