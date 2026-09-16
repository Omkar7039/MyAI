from __future__ import annotations

from dataclasses import dataclass

from experience.adaptive_strategy import AdaptiveStrategyRanker
from experience.effectiveness_policy import EffectivenessAwarePolicy
from experience.effectiveness_ranker import (
    EffectivenessAwareRanker,
)
from experience.learning_effectiveness_aggregate import (
    LearningEffectivenessAggregate,
)
from experience.learning_policy import LearningPolicyDecision
from experience.learning_signal import LearningSignal


@dataclass(frozen=True)
class EffectivenessRoutingDecision:
    strategy: str
    learned: bool
    confidence: float
    reason: str


class EffectivenessAwareRouter:
    """
    Route using adaptive strategy performance plus repeated
    effectiveness evidence.

    The normal default strategy remains the safe fallback.
    """

    def __init__(
        self,
        *,
        adaptive_ranker: AdaptiveStrategyRanker | None = None,
        effectiveness_ranker: EffectivenessAwareRanker | None = None,
        effectiveness_policy: EffectivenessAwarePolicy | None = None,
    ):
        self.adaptive_ranker = (
            adaptive_ranker or AdaptiveStrategyRanker()
        )
        self.effectiveness_ranker = (
            effectiveness_ranker or EffectivenessAwareRanker()
        )
        self.effectiveness_policy = (
            effectiveness_policy
            or EffectivenessAwarePolicy()
        )

    def route(
        self,
        *,
        default_strategy: str,
        signals: tuple[LearningSignal, ...]
        | list[LearningSignal],
        utility_by_strategy: dict[str, float] | None = None,
        effectiveness_by_strategy: dict[
            str,
            LearningEffectivenessAggregate,
        ]
        | None = None,
    ) -> EffectivenessRoutingDecision:
        default = default_strategy.strip()

        if not default:
            raise ValueError(
                "default_strategy must not be empty"
            )

        adaptive = self.adaptive_ranker.rank(
            signals,
            utility_by_strategy,
        )

        if not adaptive:
            return EffectivenessRoutingDecision(
                strategy=default,
                learned=False,
                confidence=0.0,
                reason=(
                    "no adaptive strategy evidence; "
                    "using default"
                ),
            )

        effectiveness = self.effectiveness_ranker.rank(
            adaptive,
            effectiveness_by_strategy,
        )

        if not effectiveness:
            return EffectivenessRoutingDecision(
                strategy=default,
                learned=False,
                confidence=0.0,
                reason=(
                    "no effectiveness strategy evidence; "
                    "using default"
                ),
            )

        best = effectiveness[0]

        base_decision = LearningPolicyDecision(
            allowed=True,
            strategy=best.strategy,
            confidence=best.score,
            reason="adaptive candidate available",
        )

        aggregate = None
        if effectiveness_by_strategy is not None:
            aggregate = effectiveness_by_strategy.get(
                best.strategy
            )

        if aggregate is None:
            return EffectivenessRoutingDecision(
                strategy=default,
                learned=False,
                confidence=best.score,
                reason=(
                    "no effectiveness history for selected "
                    "strategy; using default"
                ),
            )

        policy = self.effectiveness_policy.decide(
            learning_decision=base_decision,
            effectiveness=aggregate,
        )

        if not policy.allowed or not policy.strategy:
            return EffectivenessRoutingDecision(
                strategy=default,
                learned=False,
                confidence=policy.confidence,
                reason=(
                    f"effectiveness policy rejected strategy: "
                    f"{policy.reason}; using default"
                ),
            )

        return EffectivenessRoutingDecision(
            strategy=policy.strategy,
            learned=True,
            confidence=policy.confidence,
            reason=policy.reason,
        )
