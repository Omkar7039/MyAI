from __future__ import annotations

from dataclasses import dataclass

from experience.adaptive_strategy import (
    AdaptiveStrategyRanker,
)
from experience.learning_policy import LearningPolicy
from experience.learning_control import LearningControlAdapter
from experience.learning_signal import LearningSignal


@dataclass(frozen=True)
class LearningRouteDecision:
    strategy: str
    learned: bool
    confidence: float
    reason: str


class LearningAwareStrategyRouter:
    """
    Select a strategy using historical learning evidence when policy
    permits it. Otherwise return the caller-provided default strategy.

    Learning never overrides the default when evidence is insufficient.
    """

    def __init__(
        self,
        *,
        ranker: AdaptiveStrategyRanker | None = None,
        policy: LearningPolicy | None = None,
        control: LearningControlAdapter | None = None,
    ):
        self.ranker = ranker or AdaptiveStrategyRanker()
        self.policy = policy or LearningPolicy()
        self.control = control

    def route(
        self,
        *,
        default_strategy: str,
        signals: tuple[LearningSignal, ...]
        | list[LearningSignal],
        utility_by_strategy: dict[str, float] | None = None,
        baseline_score_by_strategy: dict[str, float] | None = None,
        learned_score_by_strategy: dict[str, float] | None = None,
    ) -> LearningRouteDecision:
        normalized_default = default_strategy.strip()

        if not normalized_default:
            raise ValueError("default_strategy must not be empty")

        ranked = self.ranker.rank(
            signals,
            utility_by_strategy,
        )

        if not ranked:
            return LearningRouteDecision(
                strategy=normalized_default,
                learned=False,
                confidence=0.0,
                reason="no historical strategy evidence; using default",
            )

        decision = self.policy.decide(ranked[0])

        if decision.allowed and decision.strategy:
            if (
                self.control is not None
                and baseline_score_by_strategy is not None
                and learned_score_by_strategy is not None
            ):
                strategy = decision.strategy

                if (
                    strategy in baseline_score_by_strategy
                    and strategy in learned_score_by_strategy
                ):
                    control_decision = self.control.evaluate(
                        strategy=strategy,
                        baseline_score=baseline_score_by_strategy[strategy],
                        learned_score=learned_score_by_strategy[strategy],
                    )

                    if not control_decision.allowed:
                        return LearningRouteDecision(
                            strategy=normalized_default,
                            learned=False,
                            confidence=decision.confidence,
                            reason=(
                                "learning control blocked historical strategy: "
                                f"{control_decision.reason}; using default"
                            ),
                        )

                    return LearningRouteDecision(
                        strategy=strategy,
                        learned=True,
                        confidence=decision.confidence,
                        reason=(
                            "historical strategy accepted by learning policy "
                            "and learning control"
                        ),
                    )

            return LearningRouteDecision(
                strategy=decision.strategy,
                learned=True,
                confidence=decision.confidence,
                reason=(
                    "historical strategy evidence accepted by learning policy"
                ),
            )

        return LearningRouteDecision(
            strategy=normalized_default,
            learned=False,
            confidence=decision.confidence,
            reason=(
                f"learning policy rejected historical strategy: "
                f"{decision.reason}; using default"
            ),
        )
