from __future__ import annotations

from dataclasses import dataclass

from verification.mutation_gap import MutationGapAssessment
from verification.post_repair_loop import PostRepairVerificationLoop
from verification.strategy_selector import (
    VerificationStrategy,
    VerificationStrategyDecision,
)
from verification.test_quality import TestQualityAssessment
from verification.weak_test_detector import WeakTestAssessment


@dataclass(frozen=True)
class VerificationBenchmarkCase:
    name: str
    expected_strategy: VerificationStrategy
    expected_passed: bool


@dataclass(frozen=True)
class VerificationBenchmarkResult:
    total_cases: int
    passed_cases: int
    failed_cases: int
    accuracy: float
    passed: bool


class VerificationBenchmark:
    def run(self) -> VerificationBenchmarkResult:
        cases = self._cases()
        passed = 0

        for case in cases:
            strategy = self._select(case.name)
            verification = self._verify(strategy, case.name)

            if (
                strategy.strategy == case.expected_strategy
                and verification == case.expected_passed
            ):
                passed += 1

        total = len(cases)
        failed = total - passed
        accuracy = (passed / total) * 100.0 if total else 0.0

        return VerificationBenchmarkResult(
            total_cases=total,
            passed_cases=passed,
            failed_cases=failed,
            accuracy=accuracy,
            passed=(failed == 0),
        )

    @staticmethod
    def _quality(
        valid: bool = True,
        score: float = 80.0,
    ) -> TestQualityAssessment:
        return TestQualityAssessment(
            valid=valid,
            assertion_count=4,
            statement_count=4,
            import_count=0,
            function_count=0,
            score=score,
            reasons=(),
        )

    @staticmethod
    def _weak(
        weak: bool = False,
    ) -> WeakTestAssessment:
        return WeakTestAssessment(
            weak=weak,
            score=80.0 if not weak else 40.0,
            assertion_count=4 if not weak else 1,
            duplicate_assertion_count=0,
            trivial_assertion_count=0,
            reasons=(),
        )

    @staticmethod
    def _mutation(
        survived: int = 0,
    ) -> MutationGapAssessment:
        total = 5
        killed = total - survived

        return MutationGapAssessment(
            total_mutations=total,
            killed_mutations=killed,
            survived_mutations=survived,
            invalid_mutations=0,
            kill_rate=(killed / total) * 100.0,
            gap_rate=(survived / total) * 100.0,
            strong=survived == 0,
            reasons=(),
        )

    @classmethod
    def _select(
        cls,
        name: str,
    ) -> VerificationStrategyDecision:
        from verification.strategy_selector import VerificationStrategySelector

        selector = VerificationStrategySelector()

        if name == "invalid":
            return selector.select(
                quality=cls._quality(valid=False, score=0.0),
                weak=cls._weak(True),
            )

        if name == "weak":
            return selector.select(
                quality=cls._quality(),
                weak=cls._weak(True),
            )

        if name == "mutation_gap":
            return selector.select(
                quality=cls._quality(),
                weak=cls._weak(),
                mutation=cls._mutation(2),
            )

        if name == "property":
            return selector.select(
                quality=cls._quality(),
                weak=cls._weak(),
                mutation=cls._mutation(),
                operation="sort",
            )

        return selector.select(
            quality=cls._quality(),
            weak=cls._weak(),
            mutation=cls._mutation(),
            operation="calculate",
        )

    @staticmethod
    def _verify(
        strategy: VerificationStrategyDecision,
        name: str,
    ) -> bool:
        loop = PostRepairVerificationLoop(max_attempts=2)

        if name == "invalid":
            result = loop.verify(
                strategy=strategy,
                run_standard=lambda: True,
                strengthen=lambda: True,
            )
            return result.passed

        if name == "weak":
            result = loop.verify(
                strategy=strategy,
                run_standard=lambda: True,
                strengthen=lambda: True,
            )
            return result.passed

        if name == "mutation_gap":
            state = {"calls": 0}

            def mutation():
                state["calls"] += 1
                return VerificationBenchmark._mutation(
                    0 if state["calls"] == 2 else 1
                )

            result = loop.verify(
                strategy=strategy,
                run_standard=lambda: True,
                run_mutation=mutation,
            )
            return result.passed

        if name == "property":
            result = loop.verify(
                strategy=strategy,
                run_standard=lambda: True,
                run_property=lambda: True,
            )
            return result.passed

        result = loop.verify(
            strategy=strategy,
            run_standard=lambda: True,
        )
        return result.passed

    @staticmethod
    def _cases() -> tuple[VerificationBenchmarkCase, ...]:
        return (
            VerificationBenchmarkCase(
                name="invalid",
                expected_strategy=VerificationStrategy.STRENGTHEN,
                expected_passed=True,
            ),
            VerificationBenchmarkCase(
                name="weak",
                expected_strategy=VerificationStrategy.STRENGTHEN,
                expected_passed=True,
            ),
            VerificationBenchmarkCase(
                name="mutation_gap",
                expected_strategy=VerificationStrategy.MUTATION,
                expected_passed=True,
            ),
            VerificationBenchmarkCase(
                name="property",
                expected_strategy=VerificationStrategy.PROPERTY,
                expected_passed=True,
            ),
            VerificationBenchmarkCase(
                name="standard",
                expected_strategy=VerificationStrategy.STANDARD,
                expected_passed=True,
            ),
        )
