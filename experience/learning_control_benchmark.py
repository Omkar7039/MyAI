from __future__ import annotations

from dataclasses import dataclass

from experience.safe_learning_control import SafeLearningControl
from experience.learning_signal import LearningSignal


@dataclass(frozen=True)
class LearningControlBenchmarkCase:
    name: str
    strategy: str
    signals: tuple[LearningSignal, ...]
    task_family: str | None
    allow_cross_task: bool
    baseline_score: float
    learned_score: float
    expected_allowed: bool
    expected_rollback: bool


@dataclass(frozen=True)
class LearningControlBenchmarkResult:
    name: str
    passed: bool
    allowed: bool
    rollback: bool
    severity: str


class LearningControlBenchmark:
    def __init__(
        self,
        controller: SafeLearningControl | None = None,
    ):
        self.controller = controller or SafeLearningControl()

    @staticmethod
    def cases() -> tuple[LearningControlBenchmarkCase, ...]:
        from experience.learning_signal import LearningSignalCollector

        collector = LearningSignalCollector()

        parser = collector.repair_success(
            "parser task",
            strategy="property",
            score=95.0,
            metadata="task_family=parser",
        )

        database = collector.repair_success(
            "database task",
            strategy="property",
            score=95.0,
            metadata="task_family=database",
        )

        return (
            LearningControlBenchmarkCase(
                name="safe improvement",
                strategy="property",
                signals=(parser,),
                task_family="parser",
                allow_cross_task=True,
                baseline_score=70.0,
                learned_score=95.0,
                expected_allowed=True,
                expected_rollback=False,
            ),
            LearningControlBenchmarkCase(
                name="neutral outcome",
                strategy="property",
                signals=(parser,),
                task_family="parser",
                allow_cross_task=True,
                baseline_score=85.0,
                learned_score=85.0,
                expected_allowed=True,
                expected_rollback=False,
            ),
            LearningControlBenchmarkCase(
                name="low regression",
                strategy="property",
                signals=(parser,),
                task_family="parser",
                allow_cross_task=True,
                baseline_score=90.0,
                learned_score=82.0,
                expected_allowed=True,
                expected_rollback=False,
            ),
            LearningControlBenchmarkCase(
                name="high regression",
                strategy="property",
                signals=(parser,),
                task_family="parser",
                allow_cross_task=True,
                baseline_score=95.0,
                learned_score=40.0,
                expected_allowed=False,
                expected_rollback=True,
            ),
            LearningControlBenchmarkCase(
                name="cross task blocked",
                strategy="property",
                signals=(database,),
                task_family="parser",
                allow_cross_task=True,
                baseline_score=70.0,
                learned_score=95.0,
                expected_allowed=False,
                expected_rollback=False,
            ),
        )

    def run(self) -> tuple[LearningControlBenchmarkResult, ...]:
        results: list[LearningControlBenchmarkResult] = []

        for case in self.cases():
            decision = self.controller.evaluate(
                strategy=case.strategy,
                signals=case.signals,
                task_family=case.task_family,
                allow_cross_task=case.allow_cross_task,
                baseline_score=case.baseline_score,
                learned_score=case.learned_score,
            )

            passed = (
                decision.allowed == case.expected_allowed
                and decision.rollback == case.expected_rollback
            )

            results.append(
                LearningControlBenchmarkResult(
                    name=case.name,
                    passed=passed,
                    allowed=decision.allowed,
                    rollback=decision.rollback,
                    severity=decision.severity,
                )
            )

        return tuple(results)

    def all_passed(self) -> bool:
        return all(result.passed for result in self.run())
