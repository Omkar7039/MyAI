from __future__ import annotations

from dataclasses import dataclass

from experience.governed_learning import (
    GovernedLearningAdapter,
)
from experience.learning_signal import LearningSignal


@dataclass(frozen=True)
class GovernedRouteDecision:
    strategy: str
    learned: bool
    governed: bool
    confidence: float
    reason: str


class GovernedStrategyRouter:
    """
    Select a learned strategy only when the learning proposal passes
    governance. Otherwise return the caller-provided default strategy.

    This is an additive layer; the existing LearningAwareStrategyRouter
    remains unchanged.
    """

    def __init__(
        self,
        *,
        governed: GovernedLearningAdapter | None = None,
    ):
        self.governed = governed or GovernedLearningAdapter()

    def route(
        self,
        *,
        default_strategy: str,
        signals: tuple[LearningSignal, ...]
        | list[LearningSignal],
        baseline_score: float,
        task_family: str | None = None,
        allow_cross_task: bool = False,
        utility_by_strategy: dict[str, float] | None = None,
    ) -> GovernedRouteDecision:
        normalized_default = default_strategy.strip()

        if not normalized_default:
            raise ValueError(
                "default_strategy must not be empty"
            )

        result = self.governed.evaluate(
            signals=signals,
            baseline_score=baseline_score,
            task_family=task_family,
            allow_cross_task=allow_cross_task,
            utility_by_strategy=utility_by_strategy,
        )

        if (
            result.safe
            and result.governance is not None
            and result.governance.approved
            and result.governance.applied
            and result.candidate_strategy
        ):
            return GovernedRouteDecision(
                strategy=result.candidate_strategy,
                learned=True,
                governed=True,
                confidence=result.governance.confidence,
                reason="learned strategy approved by governance",
            )

        confidence = 0.0

        if result.governance is not None:
            confidence = result.governance.confidence
        elif result.proposal is not None:
            confidence = result.proposal.confidence

        return GovernedRouteDecision(
            strategy=normalized_default,
            learned=False,
            governed=result.governance is not None,
            confidence=confidence,
            reason=(
                f"governance rejected learned strategy: "
                f"{result.reason}; using default"
            ),
        )
