from __future__ import annotations

from dataclasses import dataclass

from experience.learning_control import LearningControlAdapter
from experience.learning_router import LearningAwareStrategyRouter
from experience.learning_signal import LearningSignal


@dataclass(frozen=True)
class VerificationRouteDecision:
    strategy: str
    learned: bool
    confidence: float
    reason: str


class LearningAwareVerificationRouter:
    """
    Choose a verification strategy using historical learning evidence.

    The existing verification strategy remains the safe fallback.
    """

    def __init__(
        self,
        *,
        router: LearningAwareStrategyRouter | None = None,
        control: LearningControlAdapter | None = None,
    ):
        self.router = router or LearningAwareStrategyRouter()
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
    ) -> VerificationRouteDecision:
        route_kwargs = {
            "default_strategy": default_strategy,
            "signals": signals,
            "utility_by_strategy": utility_by_strategy,
        }

        if baseline_score_by_strategy is not None:
            route_kwargs["baseline_score_by_strategy"] = baseline_score_by_strategy

        if learned_score_by_strategy is not None:
            route_kwargs["learned_score_by_strategy"] = learned_score_by_strategy

        decision = self.router.route(**route_kwargs)

        if (
            self.control is not None
            and decision.learned
            and baseline_score_by_strategy is not None
            and learned_score_by_strategy is not None
            and decision.strategy in baseline_score_by_strategy
            and decision.strategy in learned_score_by_strategy
        ):
            control_decision = self.control.evaluate(
                strategy=decision.strategy,
                baseline_score=baseline_score_by_strategy[decision.strategy],
                learned_score=learned_score_by_strategy[decision.strategy],
            )

            if not control_decision.allowed:
                return VerificationRouteDecision(
                    strategy=default_strategy.strip(),
                    learned=False,
                    confidence=decision.confidence,
                    reason=(
                        "learning control blocked verification strategy: "
                        f"{control_decision.reason}; using default"
                    ),
                )

            return VerificationRouteDecision(
                strategy=decision.strategy,
                learned=True,
                confidence=decision.confidence,
                reason="verification strategy accepted by learning control",
            )

        return VerificationRouteDecision(
            strategy=decision.strategy,
            learned=decision.learned,
            confidence=decision.confidence,
            reason=decision.reason,
        )
