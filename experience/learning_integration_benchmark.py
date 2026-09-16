from __future__ import annotations

from dataclasses import dataclass

from experience.adaptive_strategy import AdaptiveStrategyRanker
from experience.learning_feedback import LearningFeedbackBuilder
from experience.learning_persistence import LearningPersistenceBridge
from experience.learning_policy import LearningPolicy
from experience.learning_signal import LearningSignalCollector
from experience.learning_router import LearningAwareStrategyRouter
from experience.store import ExperienceStore


@dataclass(frozen=True)
class LearningIntegrationCase:
    name: str
    expected_learned: bool
    expected_strategy: str


@dataclass(frozen=True)
class LearningIntegrationBenchmarkResult:
    total_cases: int
    passed_cases: int
    failed_cases: int
    accuracy: float
    passed: bool


class LearningIntegrationBenchmark:
    """
    Validate the 6.20 learning integration path:

    outcome
      -> feedback
      -> signals
      -> persistence
      -> adaptive ranking
      -> policy
      -> routing

    The benchmark uses a temporary ExperienceStore and performs no
    model inference.
    """

    def run(self) -> LearningIntegrationBenchmarkResult:
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

        return LearningIntegrationBenchmarkResult(
            total_cases=total,
            passed_cases=passed,
            failed_cases=failed,
            accuracy=accuracy,
            passed=(failed == 0),
        )

    @staticmethod
    def _evaluate(name: str) -> tuple[bool, str]:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            store = ExperienceStore(
                f"{directory}/learning.db"
            )

            feedback_builder = LearningFeedbackBuilder()
            persistence = LearningPersistenceBridge(store)
            collector = LearningSignalCollector()
            ranker = AdaptiveStrategyRanker()
            policy = LearningPolicy(
                min_observations=3,
            )
            router = LearningAwareStrategyRouter()

            if name == "strong_property":
                feedbacks = [
                    feedback_builder.build(
                        task=f"property-{index}",
                        strategy="property",
                        repair_success=True,
                        verification_success=True,
                        repair_score=95.0,
                        verification_score=95.0,
                    )
                    for index in range(3)
                ]

                signals = [
                    signal
                    for feedback in feedbacks
                    for signal in feedback.signals
                ]

                persistence.persist(signals)

                ranked = ranker.rank(
                    signals,
                    {"property": 95.0},
                )

                decision = policy.decide(ranked[0])

                routed = router.route(
                    default_strategy="standard",
                    signals=signals,
                    utility_by_strategy={"property": 95.0},
                )

                return (
                    decision.allowed and routed.learned,
                    routed.strategy,
                )

            if name == "insufficient":
                feedback = feedback_builder.build(
                    task="one",
                    strategy="property",
                    repair_success=True,
                    verification_success=True,
                    repair_score=95.0,
                    verification_score=95.0,
                )

                signals = list(feedback.signals)

                persistence.persist(signals)

                routed = router.route(
                    default_strategy="standard",
                    signals=signals,
                    utility_by_strategy={"property": 95.0},
                )

                return routed.learned, routed.strategy

            if name == "failed_standard":
                signals = []

                for index in range(3):
                    feedback = feedback_builder.build(
                        task=f"failed-{index}",
                        strategy="standard",
                        repair_success=False,
                        verification_success=False,
                        repair_score=0.0,
                        verification_score=0.0,
                    )
                    signals.extend(feedback.signals)

                persistence.persist(signals)

                routed = router.route(
                    default_strategy="property",
                    signals=signals,
                    utility_by_strategy={"standard": 0.0},
                )

                return routed.learned, routed.strategy

            feedback = feedback_builder.build(
                task="fallback",
                strategy="standard",
                repair_success=True,
                verification_success=True,
                repair_score=90.0,
                verification_score=90.0,
            )

            signals = list(feedback.signals)
            persisted = persistence.persist(signals)

            # Ensure the persistence path actually produced records.
            if persisted.persisted == 0:
                raise AssertionError(
                    "benchmark persistence unexpectedly stored no records"
                )

            routed = router.route(
                default_strategy="standard",
                signals=signals,
            )

            return routed.learned, routed.strategy

    @staticmethod
    def _cases() -> tuple[LearningIntegrationCase, ...]:
        return (
            LearningIntegrationCase(
                name="strong_property",
                expected_learned=True,
                expected_strategy="property",
            ),
            LearningIntegrationCase(
                name="insufficient",
                expected_learned=False,
                expected_strategy="standard",
            ),
            LearningIntegrationCase(
                name="failed_standard",
                expected_learned=False,
                expected_strategy="property",
            ),
            LearningIntegrationCase(
                name="fallback",
                expected_learned=False,
                expected_strategy="standard",
            ),
        )
