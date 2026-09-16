from __future__ import annotations

from dataclasses import dataclass

from experience.adaptive_strategy import AdaptiveStrategyRanker
from experience.learning_policy import LearningPolicy
from experience.learning_signal import LearningSignalCollector


@dataclass(frozen=True)
class LearningBenchmarkCase:
    name: str
    expected_allowed: bool
    expected_strategy: str | None


@dataclass(frozen=True)
class LearningBenchmarkResult:
    total_cases: int
    passed_cases: int
    failed_cases: int
    accuracy: float
    passed: bool


class LearningBenchmark:
    """
    Validate the learning pipeline:

    signals
      -> adaptive strategy ranking
      -> learning policy
      -> allow / reject

    The benchmark is deterministic and does not invoke model inference.
    """

    def run(self) -> LearningBenchmarkResult:
        cases = self._cases()
        passed = 0

        for case in cases:
            decision = self._evaluate(case.name)

            if (
                decision.allowed == case.expected_allowed
                and decision.strategy == case.expected_strategy
            ):
                passed += 1

        total = len(cases)
        failed = total - passed
        accuracy = (passed / total) * 100.0 if total else 0.0

        return LearningBenchmarkResult(
            total_cases=total,
            passed_cases=passed,
            failed_cases=failed,
            accuracy=accuracy,
            passed=(failed == 0),
        )

    @staticmethod
    def _evaluate(name: str):
        collector = LearningSignalCollector()
        ranker = AdaptiveStrategyRanker()

        if name == "strong_history":
            signals = []

            for index in range(5):
                signals.append(
                    collector.repair_success(
                        f"fix task {index}",
                        strategy="property",
                        score=90.0,
                    )
                )

            ranked = ranker.rank(
                signals,
                {"property": 90.0},
            )

            return LearningPolicy().decide(ranked[0])

        if name == "insufficient_history":
            signals = [
                collector.repair_success(
                    "fix task",
                    strategy="property",
                    score=90.0,
                ),
            ]

            ranked = ranker.rank(
                signals,
                {"property": 90.0},
            )

            return LearningPolicy().decide(ranked[0])

        if name == "weak_strategy":
            signals = [
                collector.repair_success(
                    "a",
                    strategy="standard",
                    score=60.0,
                ),
                collector.repair_failure(
                    "b",
                    strategy="standard",
                    score=0.0,
                ),
                collector.repair_failure(
                    "c",
                    strategy="standard",
                    score=0.0,
                ),
            ]

            ranked = ranker.rank(
                signals,
                {"standard": 20.0},
            )

            return LearningPolicy().decide(ranked[0])

        if name == "successful_but_penalized":
            signals = [
                collector.repair_success(
                    "a",
                    strategy="mutation",
                    score=90.0,
                ),
                collector.repair_success(
                    "b",
                    strategy="mutation",
                    score=90.0,
                ),
                collector.repair_success(
                    "c",
                    strategy="mutation",
                    score=90.0,
                ),
                collector.retry(
                    "a",
                    strategy="mutation",
                ),
                collector.rollback(
                    "a",
                    strategy="mutation",
                ),
            ]

            ranked = ranker.rank(
                signals,
                {"mutation": 80.0},
            )

            return LearningPolicy().decide(ranked[0])

        signals = [
            collector.repair_success(
                "safe default",
                strategy="standard",
                score=90.0,
            ),
            collector.repair_success(
                "safe default 2",
                strategy="standard",
                score=90.0,
            ),
            collector.repair_success(
                "safe default 3",
                strategy="standard",
                score=90.0,
            ),
        ]

        ranked = ranker.rank(signals)

        return LearningPolicy().decide(ranked[0])

    @staticmethod
    def _cases() -> tuple[LearningBenchmarkCase, ...]:
        return (
            LearningBenchmarkCase(
                name="strong_history",
                expected_allowed=True,
                expected_strategy="property",
            ),
            LearningBenchmarkCase(
                name="insufficient_history",
                expected_allowed=False,
                expected_strategy="property",
            ),
            LearningBenchmarkCase(
                name="weak_strategy",
                expected_allowed=False,
                expected_strategy="standard",
            ),
            LearningBenchmarkCase(
                name="successful_but_penalized",
                expected_allowed=True,
                expected_strategy="mutation",
            ),
            LearningBenchmarkCase(
                name="standard_fallback",
                expected_allowed=True,
                expected_strategy="standard",
            ),
        )
