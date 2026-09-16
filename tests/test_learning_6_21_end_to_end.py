from tempfile import TemporaryDirectory

from agents.learning_debug_context import (
    LearningDebugContextBuilder,
)
from agents.learning_multifile_context import (
    LearningMultiFileContextBuilder,
)
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
from experience.learning_orchestrator import (
    UnifiedLearningRouter,
)
from experience.learning_policy import LearningPolicy
from experience.learning_safety import LearningSafetyGuard
from experience.learning_signal import LearningSignalCollector
from experience.outcome_capture import AutomaticOutcomeCapture
from experience.store import ExperienceStore
from verification.learning_verification_context import (
    LearningVerificationContextBuilder,
)


def test_complete_6_21_learning_lifecycle():
    with TemporaryDirectory() as directory:
        store = ExperienceStore(
            f"{directory}/learning.db"
        )

        capture = AutomaticOutcomeCapture()
        persistence = AutomaticLearningPersistence(store)

        # Generate enough successful history for learning policy.
        for index in range(3):
            captured = capture.capture(
                task=f"calculator-{index}",
                strategy="property",
                repair_success=True,
                verification_success=True,
                repair_score=95.0,
                verification_score=95.0,
                metadata="task_family=calculator",
            )

            persisted = persistence.persist(captured)

            assert persisted.persisted is True
            assert persisted.persistence.persisted == 2

        # Historical retrieval.
        retriever = HistoricalLearningRetriever(store)
        historical = HistoricalLearningInjector(
            retriever
        ).recent()

        assert historical.retrieved == 6
        assert historical.utility_by_strategy == {
            "property": 95.0
        }

        # Cross-task isolation.
        safety = LearningSafetyGuard()

        safe = safety.filter(
            task_family="calculator",
            signals=historical.signals,
            allow_cross_task=True,
        )

        assert safe.allowed is True
        assert len(safe.signals) == 6

        isolated = safety.filter(
            task_family="database",
            signals=historical.signals,
            allow_cross_task=True,
        )

        assert isolated.allowed is False
        assert isolated.signals == ()

        # Adaptive strategy ranking.
        ranked = AdaptiveStrategyRanker().rank(
            safe.signals,
            historical.utility_by_strategy,
        )

        assert ranked
        assert ranked[0].strategy == "property"
        assert ranked[0].success_rate == 100.0

        # Learning policy.
        policy = LearningPolicy(
            min_observations=3,
        )

        decision = policy.decide(ranked[0])

        assert decision.allowed is True
        assert decision.strategy == "property"

        # Learning-aware unified routing.
        routing = UnifiedLearningRouter().route(
            default_repair_strategy="standard",
            default_verification_strategy="standard",
            signals=safe.signals,
            utility_by_strategy=historical.utility_by_strategy,
        )

        assert routing.repair.strategy == "property"
        assert routing.repair.learned is True
        assert routing.verification.strategy == "property"
        assert routing.verification.learned is True

        # Advisory debugging context.
        debug_context = LearningDebugContextBuilder().build(
            task="debug calculator",
            injection=historical,
        )

        assert debug_context.strategies == ("property",)
        assert any(
            "advisory context" in item
            for item in debug_context.guidance
        )
        assert any(
            "Current source, tests, and investigation evidence"
            in item
            for item in debug_context.guidance
        )

        # Advisory multi-file repair context.
        multifile_context = LearningMultiFileContextBuilder().build(
            task="repair calculator project",
            injection=historical,
        )

        assert multifile_context.strategies == ("property",)
        assert any(
            "Current repository state" in item
            for item in multifile_context.guidance
        )
        assert any(
            "rollback safeguards remain mandatory" in item
            for item in multifile_context.guidance
        )

        # Advisory verification context.
        verification_context = (
            LearningVerificationContextBuilder().build(
                task="verify calculator repair",
                injection=historical,
            )
        )

        assert verification_context.strategies == ("property",)
        assert any(
            "Current tests and verification evidence"
            in item
            for item in verification_context.guidance
        )


def test_6_21_insufficient_history_does_not_learn():
    with TemporaryDirectory() as directory:
        store = ExperienceStore(
            f"{directory}/learning.db"
        )

        captured = AutomaticOutcomeCapture().capture(
            task="single",
            strategy="property",
            repair_success=True,
            verification_success=True,
            repair_score=100.0,
            verification_score=100.0,
            metadata="task_family=calculator",
        )

        AutomaticLearningPersistence(store).persist(
            captured
        )

        historical = HistoricalLearningInjector(
            HistoricalLearningRetriever(store)
        ).recent()

        routing = UnifiedLearningRouter().route(
            default_repair_strategy="standard",
            default_verification_strategy="standard",
            signals=historical.signals,
            utility_by_strategy=historical.utility_by_strategy,
        )

        assert routing.repair.learned is False
        assert routing.repair.strategy == "standard"
        assert routing.verification.learned is False
        assert routing.verification.strategy == "standard"


def test_6_21_unrelated_history_cannot_influence_routing():
    with TemporaryDirectory() as directory:
        store = ExperienceStore(
            f"{directory}/learning.db"
        )

        capture = AutomaticOutcomeCapture()
        persistence = AutomaticLearningPersistence(store)

        for index in range(3):
            captured = capture.capture(
                task=f"database-{index}",
                strategy="property",
                repair_success=True,
                verification_success=True,
                repair_score=100.0,
                verification_score=100.0,
                metadata="task_family=database",
            )

            persistence.persist(captured)

        historical = HistoricalLearningInjector(
            HistoricalLearningRetriever(store)
        ).recent()

        safe = LearningSafetyGuard().filter(
            task_family="calculator",
            signals=historical.signals,
            allow_cross_task=True,
        )

        routing = UnifiedLearningRouter().route(
            default_repair_strategy="standard",
            default_verification_strategy="standard",
            signals=safe.signals,
            utility_by_strategy=historical.utility_by_strategy,
        )

        assert safe.allowed is False
        assert routing.repair.learned is False
        assert routing.repair.strategy == "standard"
        assert routing.verification.learned is False
        assert routing.verification.strategy == "standard"


def test_6_21_lifecycle_is_deterministic():
    def run():
        with TemporaryDirectory() as directory:
            store = ExperienceStore(
                f"{directory}/learning.db"
            )

            capture = AutomaticOutcomeCapture()
            persistence = AutomaticLearningPersistence(store)

            for index in range(3):
                captured = capture.capture(
                    task=f"task-{index}",
                    strategy="property",
                    repair_success=True,
                    verification_success=True,
                    repair_score=95.0,
                    verification_score=95.0,
                    metadata="task_family=calculator",
                )
                persistence.persist(captured)

            historical = HistoricalLearningInjector(
                HistoricalLearningRetriever(store)
            ).recent()

            safe = LearningSafetyGuard().filter(
                task_family="calculator",
                signals=historical.signals,
                allow_cross_task=True,
            )

            return UnifiedLearningRouter().route(
                default_repair_strategy="standard",
                default_verification_strategy="standard",
                signals=safe.signals,
                utility_by_strategy=(
                    historical.utility_by_strategy
                ),
            )

    assert run() == run()
