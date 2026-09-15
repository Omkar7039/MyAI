from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from verification.mutation_gap import MutationGapAssessment
from verification.strategy_selector import (
    VerificationStrategy,
    VerificationStrategyDecision,
)


@dataclass(frozen=True)
class PostRepairVerificationResult:
    passed: bool
    attempts: int
    strategy: VerificationStrategy
    strengthened: bool
    mutation_gap: int
    reasons: tuple[str, ...]


class PostRepairVerificationLoop:
    """
    Run deterministic post-repair verification.

    The loop is deliberately callback-driven so existing project,
    mutation, property, and test infrastructure can be connected
    without adding model inference or hidden side effects.
    """

    def __init__(self, max_attempts: int = 3):
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        self.max_attempts = max_attempts

    def verify(
        self,
        *,
        strategy: VerificationStrategyDecision,
        run_standard: Callable[[], bool],
        strengthen: Callable[[], bool] | None = None,
        run_mutation: Callable[[], MutationGapAssessment] | None = None,
        run_property: Callable[[], bool] | None = None,
    ) -> PostRepairVerificationResult:
        reasons: list[str] = []
        attempts = 0
        strengthened = False
        mutation_gap = 0

        for _ in range(self.max_attempts):
            attempts += 1

            if strategy.strategy == VerificationStrategy.STRENGTHEN:
                if strengthen is None:
                    reasons.append(
                        "strengthening strategy selected but no "
                        "strengthener was provided"
                    )
                    return PostRepairVerificationResult(
                        passed=False,
                        attempts=attempts,
                        strategy=strategy.strategy,
                        strengthened=False,
                        mutation_gap=mutation_gap,
                        reasons=tuple(reasons),
                    )

                changed = strengthen()
                strengthened = strengthened or changed
                reasons.append(
                    "test strengthening executed"
                )

                if run_standard():
                    reasons.append(
                        "standard verification passed after strengthening"
                    )
                    return PostRepairVerificationResult(
                        passed=True,
                        attempts=attempts,
                        strategy=strategy.strategy,
                        strengthened=strengthened,
                        mutation_gap=mutation_gap,
                        reasons=tuple(reasons),
                    )

            elif strategy.strategy == VerificationStrategy.MUTATION:
                if run_mutation is None:
                    reasons.append(
                        "mutation strategy selected but no mutation "
                        "verifier was provided"
                    )
                    return PostRepairVerificationResult(
                        passed=False,
                        attempts=attempts,
                        strategy=strategy.strategy,
                        strengthened=strengthened,
                        mutation_gap=mutation_gap,
                        reasons=tuple(reasons),
                    )

                mutation = run_mutation()
                mutation_gap = mutation.survived_mutations

                if mutation.strong:
                    reasons.append(
                        "mutation verification passed"
                    )
                    return PostRepairVerificationResult(
                        passed=True,
                        attempts=attempts,
                        strategy=strategy.strategy,
                        strengthened=strengthened,
                        mutation_gap=mutation_gap,
                        reasons=tuple(reasons),
                    )

                reasons.append(
                    "mutation gaps remain after verification"
                )

            elif strategy.strategy == VerificationStrategy.PROPERTY:
                if run_property is None:
                    reasons.append(
                        "property strategy selected but no property "
                        "verifier was provided"
                    )
                    return PostRepairVerificationResult(
                        passed=False,
                        attempts=attempts,
                        strategy=strategy.strategy,
                        strengthened=strengthened,
                        mutation_gap=mutation_gap,
                        reasons=tuple(reasons),
                    )

                if run_property():
                    reasons.append(
                        "property verification passed"
                    )
                    return PostRepairVerificationResult(
                        passed=True,
                        attempts=attempts,
                        strategy=strategy.strategy,
                        strengthened=strengthened,
                        mutation_gap=mutation_gap,
                        reasons=tuple(reasons),
                    )

                reasons.append(
                    "property verification failed"
                )

            else:
                if run_standard():
                    reasons.append(
                        "standard verification passed"
                    )
                    return PostRepairVerificationResult(
                        passed=True,
                        attempts=attempts,
                        strategy=strategy.strategy,
                        strengthened=strengthened,
                        mutation_gap=mutation_gap,
                        reasons=tuple(reasons),
                    )

                reasons.append(
                    "standard verification failed"
                )

        reasons.append(
            "maximum post-repair verification attempts exhausted"
        )

        return PostRepairVerificationResult(
            passed=False,
            attempts=attempts,
            strategy=strategy.strategy,
            strengthened=strengthened,
            mutation_gap=mutation_gap,
            reasons=tuple(reasons),
        )
