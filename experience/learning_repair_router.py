from __future__ import annotations

from dataclasses import dataclass

from experience.learning_control import LearningControlAdapter
from experience.learning_router import LearningAwareStrategyRouter
from experience.learning_signal import LearningSignal


@dataclass(frozen=True)
class RepairRouteDecision:
    strategy: str
    learned: bool
    confidence: float
    reason: str


class LearningAwareRepairRouter:
    """
    Choose a repair strategy using historical learning evidence.

    The existing repair strategy remains the safe fallback whenever
    historical evidence is missing or below policy thresholds.
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
    ) -> RepairRouteDecision:
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
                return RepairRouteDecision(
                    strategy=default_strategy.strip(),
                    learned=False,
                    confidence=decision.confidence,
                    reason=(
                        "learning control blocked repair strategy: "
                        f"{control_decision.reason}; using default"
                    ),
                )

            return RepairRouteDecision(
                strategy=decision.strategy,
                learned=True,
                confidence=decision.confidence,
                reason="repair strategy accepted by learning control",
            )

        return RepairRouteDecision(
            strategy=decision.strategy,
            learned=decision.learned,
            confidence=decision.confidence,
            reason=decision.reason,
        )
