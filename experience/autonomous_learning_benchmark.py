from __future__ import annotations

from dataclasses import dataclass
from tempfile import TemporaryDirectory

from experience.adaptive_strategy import AdaptiveStrategyRanker
from experience.automatic_learning_persistence import (
    AutomaticLearningPersistence,
)
from experience.historical_learning import (
    HistoricalLearningRetriever,
)
from experience.historical_learning_injection import (
    HistoricalLearningInjector,
)
from experience.learning_persistence import (
    LearningPersistenceBridge,
)
from experience.learning_policy import LearningPolicy
from experience.learning_router import LearningAwareStrategyRouter
from experience.learning_signal import LearningSignalCollector
from experience.learning_safety import LearningSafetyGuard
from experience.outcome_capture import AutomaticOutcomeCapture
from experience.store import ExperienceStore


@dataclass(frozen=True)
class AutonomousLearningBenchmarkCase:
    name: str
    expected_learned: bool
    expected_strategy: str


@dataclass(frozen=True)
class AutonomousLearningBenchmarkResult:
    total_cases: int
    passed_cases: int
    failed_cases: int
    accuracy: float
    passed: bool


class AutonomousLearningBenchmark:
    """
    Validate the complete autonomous learning lifecycle:

        outcome
          -> capture
          -> persistence
          -> historical retrieval
          -> safety filtering
          -> adaptive routing

    The benchmark is deterministic and does not invoke model inference.
    """

    def run(self) -> AutonomousLearningBenchmarkResult:
        cases = self._cases()
        passed = 0

        for case in cases:
            learned, strategy = self._evaluate(case.name)

            if (
                learned == case.expected_learned
                and strategy == case.expected_strategy
            ):
                passed += 1

        total = len(cases)
        failed = total - passed
        accuracy = (
            (passed / total) * 100.0
            if total
            else 0.0
        )

        return AutonomousLearningBenchmarkResult(
            total_cases=total,
            passed_cases=passed,
            failed_cases=failed,
            accuracy=accuracy,
            passed=(failed == 0),
        )

    @staticmethod
    def _evaluate(name: str) -> tuple[bool, str]:
        with TemporaryDirectory() as directory:
            store = ExperienceStore(
                f"{directory}/autonomous.db"
            )

            capture = AutomaticOutcomeCapture()
            persistence = AutomaticLearningPersistence(store)
            retriever = HistoricalLearningRetriever(store)
            injector = HistoricalLearningInjector(retriever)

            safety = LearningSafetyGuard()
            router = LearningAwareStrategyRouter(
                policy=LearningPolicy(
                    min_observations=3,
                ),
            )

            if name == "strong_property":
                for index in range(3):
                    captured = capture.capture(
                        task=f"property-{index}",
                        strategy="property",
                        repair_success=True,
                        verification_success=True,
                        repair_score=95.0,
                        verification_score=95.0,
                        metadata="task_family=calculator",
                    )

                    persistence.persist(captured)

                historical = injector.recent()

                safe = safety.filter(
                    task_family="calculator",
                    signals=historical.signals,
                    allow_cross_task=True,
                )

                routed = router.route(
                    default_strategy="standard",
                    signals=safe.signals,
                    utility_by_strategy=(
                        historical.utility_by_strategy
                    ),
                )

                return routed.learned, routed.strategy

            if name == "insufficient":
                captured = capture.capture(
                    task="single",
                    strategy="property",
                    repair_success=True,
                    verification_success=True,
                    repair_score=100.0,
                    verification_score=100.0,
                    metadata="task_family=calculator",
                )

                persistence.persist(captured)

                historical = injector.recent()

                safe = safety.filter(
                    task_family="calculator",
                    signals=historical.signals,
                    allow_cross_task=True,
                )

                routed = router.route(
                    default_strategy="standard",
                    signals=safe.signals,
                    utility_by_strategy=(
                        historical.utility_by_strategy
                    ),
                )

                return routed.learned, routed.strategy

            if name == "isolated_family":
                captured = capture.capture(
                    task="database",
                    strategy="property",
                    repair_success=True,
                    verification_success=True,
                    repair_score=100.0,
                    verification_score=100.0,
                    metadata="task_family=database",
                )

                persistence.persist(captured)

                historical = injector.recent()

                safe = safety.filter(
                    task_family="calculator",
                    signals=historical.signals,
                    allow_cross_task=True,
                )

                routed = router.route(
                    default_strategy="standard",
                    signals=safe.signals,
                    utility_by_strategy=(
                        historical.utility_by_strategy
                    ),
                )

                return routed.learned, routed.strategy

            # Safe fallback.
            captured = capture.capture(
                task="standard",
                strategy="standard",
                repair_success=True,
                verification_success=True,
                repair_score=90.0,
                verification_score=90.0,
                metadata="task_family=general",
            )

            persistence.persist(captured)

            historical = injector.recent()

            routed = router.route(
                default_strategy="standard",
                signals=historical.signals,
                utility_by_strategy=(
                    historical.utility_by_strategy
                ),
            )

            return routed.learned, routed.strategy

    @staticmethod
    def _cases() -> tuple[AutonomousLearningBenchmarkCase, ...]:
        return (
            AutonomousLearningBenchmarkCase(
                name="strong_property",
                expected_learned=True,
                expected_strategy="property",
            ),
            AutonomousLearningBenchmarkCase(
                name="insufficient",
                expected_learned=False,
                expected_strategy="standard",
            ),
            AutonomousLearningBenchmarkCase(
                name="isolated_family",
                expected_learned=False,
                expected_strategy="standard",
            ),
            AutonomousLearningBenchmarkCase(
                name="fallback",
                expected_learned=False,
                expected_strategy="standard",
            ),
        )
