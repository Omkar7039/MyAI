from __future__ import annotations

from dataclasses import dataclass

from experience.learning_repair_router import (
    LearningAwareRepairRouter,
    RepairRouteDecision,
)
from experience.learning_signal import LearningSignal
from verification.learning_verification_router import (
    LearningAwareVerificationRouter,
    VerificationRouteDecision,
)


@dataclass(frozen=True)
class LearningRoutingDecision:
    repair: RepairRouteDecision
    verification: VerificationRouteDecision


class UnifiedLearningRouter:
    """
    Coordinate learning-aware repair and verification routing.

    Each domain retains its own safe default. Learning is advisory and
    independently guarded for repair and verification.
    """

    def __init__(
        self,
        *,
        repair_router: LearningAwareRepairRouter | None = None,
        verification_router: LearningAwareVerificationRouter | None = None,
    ):
        self.repair_router = (
            repair_router or LearningAwareRepairRouter()
        )
        self.verification_router = (
            verification_router
            or LearningAwareVerificationRouter()
        )

    def route(
        self,
        *,
        default_repair_strategy: str,
        default_verification_strategy: str,
        signals: tuple[LearningSignal, ...]
        | list[LearningSignal],
        utility_by_strategy: dict[str, float] | None = None,
        baseline_score_by_strategy: dict[str, float] | None = None,
        learned_score_by_strategy: dict[str, float] | None = None,
    ) -> LearningRoutingDecision:
        repair = self.repair_router.route(
            default_strategy=default_repair_strategy,
            signals=signals,
            utility_by_strategy=utility_by_strategy,
            baseline_score_by_strategy=baseline_score_by_strategy,
            learned_score_by_strategy=learned_score_by_strategy,
        )

        verification = self.verification_router.route(
            default_strategy=default_verification_strategy,
            signals=signals,
            utility_by_strategy=utility_by_strategy,
            baseline_score_by_strategy=baseline_score_by_strategy,
            learned_score_by_strategy=learned_score_by_strategy,
        )

        return LearningRoutingDecision(
            repair=repair,
            verification=verification,
        )
