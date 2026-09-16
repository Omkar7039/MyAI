from __future__ import annotations

from dataclasses import dataclass

from experience.continuous_learning import ContinuousLearningController


@dataclass(frozen=True)
class LearningBenchmarkCase:
    name: str
    strategy: str
    baseline_score: float
    learned_score: float
    expected_improved: bool
    expected_regression: bool
    expected_rollback: bool


@dataclass(frozen=True)
class LearningBenchmarkResult:
    name: str
    passed: bool
    improved: bool
    regression_detected: bool
    rollback: bool


class LearningEffectivenessBenchmark:
    def __init__(
        self,
        controller: ContinuousLearningController | None = None,
    ):
        self.controller = controller or ContinuousLearningController()

    @staticmethod
    def cases() -> tuple[LearningBenchmarkCase, ...]:
        return (
            LearningBenchmarkCase(
                name="strong improvement",
                strategy="strategy-improve",
                baseline_score=60.0,
                learned_score=90.0,
                expected_improved=True,
                expected_regression=False,
                expected_rollback=False,
            ),
            LearningBenchmarkCase(
                name="small improvement",
                strategy="strategy-small-improve",
                baseline_score=80.0,
                learned_score=85.0,
                expected_improved=True,
                expected_regression=False,
                expected_rollback=False,
            ),
            LearningBenchmarkCase(
                name="neutral outcome",
                strategy="strategy-neutral",
                baseline_score=80.0,
                learned_score=80.0,
                expected_improved=False,
                expected_regression=False,
                expected_rollback=False,
            ),
            LearningBenchmarkCase(
                name="medium regression",
                strategy="strategy-medium-regression",
                baseline_score=90.0,
                learned_score=70.0,
                expected_improved=False,
                expected_regression=True,
                expected_rollback=False,
            ),
            LearningBenchmarkCase(
                name="high regression",
                strategy="strategy-high-regression",
                baseline_score=90.0,
                learned_score=40.0,
                expected_improved=False,
                expected_regression=True,
                expected_rollback=True,
            ),
        )

    def run(self) -> tuple[LearningBenchmarkResult, ...]:
        results: list[LearningBenchmarkResult] = []

        for case in self.cases():
            decision = self.controller.evaluate(
                strategy=case.strategy,
                baseline_score=case.baseline_score,
                learned_score=case.learned_score,
            )

            passed = (
                decision.improved == case.expected_improved
                and decision.regression_detected == case.expected_regression
                and decision.rollback == case.expected_rollback
            )

            results.append(
                LearningBenchmarkResult(
                    name=case.name,
                    passed=passed,
                    improved=decision.improved,
                    regression_detected=decision.regression_detected,
                    rollback=decision.rollback,
                )
            )

        return tuple(results)

    def all_passed(self) -> bool:
        return all(result.passed for result in self.run())
