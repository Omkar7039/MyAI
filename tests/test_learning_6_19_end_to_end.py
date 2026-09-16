from experience.adaptive_strategy import AdaptiveStrategyRanker
from experience.learning_benchmark import LearningBenchmark
from experience.learning_policy import LearningPolicy
from experience.learning_signal import LearningSignalCollector
from experience.repair_outcome_score import RepairOutcomeScorer
from experience.strategy_tracker import SuccessfulStrategyTracker
from experience.utility import ExperienceUtilityMeasurer
from experience.verification_outcome_score import VerificationOutcomeScorer
from experience.failure_tracker import FailedStrategyTracker


def test_complete_6_19_learning_flow():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix add",
            strategy="property",
            attempts=1,
            score=95.0,
        ),
        collector.verification_success(
            "verify add",
            strategy="property",
            attempts=1,
            score=90.0,
        ),
        collector.repair_success(
            "fix parser",
            strategy="property",
            attempts=1,
            score=92.0,
        ),
        collector.verification_success(
            "verify parser",
            strategy="property",
            attempts=1,
            score=90.0,
        ),
        collector.retry(
            "retry parser",
            strategy="property",
        ),
    ]

    # 6.19.1 — learning signals
    assert len(signals) == 5

    # 6.19.2 — repair outcome scoring
    repair_score = RepairOutcomeScorer().score(
        signals[:2],
    )

    assert repair_score.successful is True
    assert repair_score.score == 90.0

    # 6.19.3 — verification outcome scoring
    verification_score = VerificationOutcomeScorer().score(
        signals[1:2],
    )

    assert verification_score.successful is True
    assert verification_score.score == 90.0

    # 6.19.4 — experience utility
    utility = ExperienceUtilityMeasurer().measure(
        baseline_score=60.0,
        observed_score=90.0,
    )

    assert utility.useful is True
    assert utility.improvement == 30.0
    assert utility.score == 60.0

    # 6.19.5 — successful strategy tracking
    successful = SuccessfulStrategyTracker().summarize(signals)

    assert len(successful) == 1
    assert successful[0].strategy == "property"
    assert successful[0].successful == 4

    # 6.19.6 — failed strategy tracking
    failures = FailedStrategyTracker().summarize(signals)

    assert len(failures) == 1
    assert failures[0].strategy == "property"
    assert failures[0].retries == 1

    # 6.19.7 — adaptive ranking
    ranked = AdaptiveStrategyRanker().rank(
        signals,
        {"property": utility.score},
    )

    assert ranked
    assert ranked[0].strategy == "property"
    assert ranked[0].score > 70.0

    # 6.19.8 — learning policy
    policy = LearningPolicy(
        min_observations=3,
    )

    decision = policy.decide(ranked[0])

    assert decision.allowed is True
    assert decision.strategy == "property"
    assert decision.confidence > 0.0

    # 6.19.9 — benchmark
    benchmark = LearningBenchmark().run()

    assert benchmark.passed is True
    assert benchmark.accuracy == 100.0


def test_6_19_blocks_insufficient_learning_history():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix",
            strategy="property",
            score=95.0,
        ),
    ]

    ranked = AdaptiveStrategyRanker().rank(
        signals,
        {"property": 95.0},
    )

    decision = LearningPolicy().decide(ranked[0])

    assert decision.allowed is False
    assert decision.strategy == "property"
    assert decision.reason == (
        "insufficient historical observations"
    )


def test_6_19_learning_is_deterministic():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "a",
            strategy="property",
            score=90.0,
        ),
        collector.repair_success(
            "b",
            strategy="property",
            score=95.0,
        ),
        collector.repair_success(
            "c",
            strategy="property",
            score=92.0,
        ),
    ]

    def run():
        ranked = AdaptiveStrategyRanker().rank(
            signals,
            {"property": 90.0},
        )

        decision = LearningPolicy().decide(ranked[0])

        return ranked, decision

    first = run()
    second = run()

    assert first == second


def test_6_19_learning_does_not_modify_signals():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix",
            strategy="standard",
            score=80.0,
        ),
        collector.verification_failure(
            "verify",
            strategy="standard",
            score=20.0,
        ),
    ]

    original = tuple(signals)

    SuccessfulStrategyTracker().summarize(signals)
    FailedStrategyTracker().summarize(signals)
    AdaptiveStrategyRanker().rank(signals)
    RepairOutcomeScorer().score(signals)
    VerificationOutcomeScorer().score(signals)

    assert tuple(signals) == original
