from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from verification.mutation_gap import MutationGapAssessment
from verification.test_quality import TestQualityAssessment
from verification.weak_test_detector import WeakTestAssessment


class VerificationStrategy(str, Enum):
    STANDARD = "standard"
    STRENGTHEN = "strengthen"
    MUTATION = "mutation"
    PROPERTY = "property"


@dataclass(frozen=True)
class VerificationStrategyDecision:
    strategy: VerificationStrategy
    priority: int
    reasons: tuple[str, ...]


class VerificationStrategySelector:
    """
    Choose a verification strategy from deterministic test-quality signals.

    Priority:
      1. Invalid/very weak tests -> strengthen
      2. Surviving mutations -> mutation
      3. Property-oriented operation -> property
      4. Otherwise -> standard
    """

    def select(
        self,
        *,
        quality: TestQualityAssessment,
        weak: WeakTestAssessment,
        mutation: MutationGapAssessment | None = None,
        operation: str | None = None,
    ) -> VerificationStrategyDecision:
        reasons: list[str] = []

        if not quality.valid:
            return VerificationStrategyDecision(
                strategy=VerificationStrategy.STRENGTHEN,
                priority=100,
                reasons=("test suite is invalid",),
            )

        if weak.weak:
            reasons.append("test suite is weak")
            return VerificationStrategyDecision(
                strategy=VerificationStrategy.STRENGTHEN,
                priority=90,
                reasons=tuple(reasons),
            )

        if mutation is not None and mutation.survived_mutations > 0:
            reasons.append("mutation gaps were detected")
            return VerificationStrategyDecision(
                strategy=VerificationStrategy.MUTATION,
                priority=80,
                reasons=tuple(reasons),
            )

        normalized = (operation or "").strip().lower()

        if normalized in {"add", "sort", "reverse"}:
            reasons.append(
                f"operation {normalized!r} supports property verification"
            )
            return VerificationStrategyDecision(
                strategy=VerificationStrategy.PROPERTY,
                priority=70,
                reasons=tuple(reasons),
            )

        reasons.append("no specialized verification gap was detected")

        return VerificationStrategyDecision(
            strategy=VerificationStrategy.STANDARD,
            priority=50,
            reasons=tuple(reasons),
        )
