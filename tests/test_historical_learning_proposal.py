from __future__ import annotations

from experience.historical_learning import (
    HistoricalLearningRetriever,
)
from experience.historical_learning_proposal import (
    HistoricalLearningProposalGenerator,
)
from experience.learning_persistence import (
    LearningPersistenceBridge,
)
from experience.learning_signal import LearningSignalCollector
from experience.store import ExperienceStore


def make_store(tmp_path):
    return ExperienceStore(
        str(tmp_path / "historical-proposal.db")
    )


def persist_property_history(
    store,
    *,
    scores=(95.0, 95.0, 95.0, 95.0, 95.0),
):
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=score,
        )
        for index, score in enumerate(scores)
    ]

    LearningPersistenceBridge(store).persist(signals)


def make_generator(store):
    return HistoricalLearningProposalGenerator(
        HistoricalLearningRetriever(store)
    )


def test_recent_history_builds_proposal(tmp_path):
    store = make_store(tmp_path)
    persist_property_history(store)

    result = make_generator(store).recent(
        baseline_score=70.0,
    )

    assert result.retrieved == 5
    assert result.candidate_strategy == "property"
    assert result.proposal is not None
    assert result.proposal.strategy == "property"
    assert result.proposal.current_score == 70.0
    assert result.proposal.proposed_score == 78.5


def test_proposal_uses_ranked_candidate_score(tmp_path):
    store = make_store(tmp_path)

    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"property-{index}",
            strategy="property",
            score=90.0,
        )
        for index in range(5)
    ] + [
        collector.repair_success(
            f"mutation-{index}",
            strategy="mutation",
            score=80.0,
        )
        for index in range(5)
    ]

    LearningPersistenceBridge(store).persist(signals)

    result = make_generator(store).recent(
        baseline_score=70.0,
        utility_by_strategy={
            "property": 100.0,
            "mutation": 0.0,
        },
    )

    assert result.candidate_strategy == "property"
    assert result.proposal is not None
    assert result.proposal.proposed_score > 80.0


def test_search_builds_proposal_from_matching_history(tmp_path):
    store = make_store(tmp_path)

    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix parser",
            strategy="property",
            score=95.0,
        ),
        collector.repair_success(
            "fix database",
            strategy="standard",
            score=70.0,
        ),
    ]

    LearningPersistenceBridge(store).persist(signals)

    result = make_generator(store).search(
        query="parser",
        baseline_score=70.0,
    )

    assert result.retrieved == 1
    assert result.candidate_strategy == "property"
    assert result.proposal is not None
    assert result.proposal.strategy == "property"


def test_empty_history_returns_no_proposal(tmp_path):
    result = make_generator(
        make_store(tmp_path)
    ).recent(
        baseline_score=70.0,
    )

    assert result.proposal is None
    assert result.candidate_strategy is None
    assert result.retrieved == 0
    assert result.source_experience_ids == ()
    assert "no historical" in result.reason


def test_archived_history_returns_no_proposal(tmp_path):
    store = make_store(tmp_path)

    collector = LearningSignalCollector()

    signal = collector.repair_success(
        "archived",
        strategy="property",
        score=95.0,
    )

    persisted = LearningPersistenceBridge(store).persist(
        [signal]
    )

    store.archive(persisted.experience_ids[0])

    result = make_generator(store).recent(
        baseline_score=70.0,
    )

    assert result.proposal is None
    assert result.candidate_strategy is None
    assert result.retrieved == 0


def test_regressed_candidate_produces_regression_proposal(tmp_path):
    store = make_store(tmp_path)
    persist_property_history(
        store,
        scores=(40.0, 40.0, 40.0, 40.0, 40.0),
    )

    result = make_generator(store).recent(
        baseline_score=90.0,
    )

    assert result.proposal is not None
    assert result.proposal.regression_detected is True
    assert result.proposal.regression_severity == "high"
    assert result.proposal.improvement < 0.0


def test_source_experience_ids_are_preserved(tmp_path):
    store = make_store(tmp_path)
    persist_property_history(store)

    result = make_generator(store).recent(
        baseline_score=70.0,
        limit=3,
    )

    assert result.retrieved == 3
    assert len(result.source_experience_ids) == 3


def test_limit_is_forwarded(tmp_path):
    store = make_store(tmp_path)
    persist_property_history(store)

    result = make_generator(store).recent(
        baseline_score=70.0,
        limit=2,
    )

    assert result.retrieved == 2
    assert result.proposal is not None


def test_custom_ranker_is_respected(tmp_path):
    from experience.adaptive_strategy import AdaptiveStrategyRanker

    class EmptyRanker(AdaptiveStrategyRanker):
        def rank(self, signals, utility_by_strategy=None):
            return ()

    store = make_store(tmp_path)
    persist_property_history(store)

    generator = HistoricalLearningProposalGenerator(
        HistoricalLearningRetriever(store),
        ranker=EmptyRanker(),
    )

    result = generator.recent(
        baseline_score=70.0,
    )

    assert result.proposal is None
    assert result.candidate_strategy is None
    assert "no usable strategy" in result.reason


def test_result_is_deterministic(tmp_path):
    store = make_store(tmp_path)
    persist_property_history(store)

    generator = make_generator(store)

    first = generator.recent(
        baseline_score=70.0,
    )
    second = generator.recent(
        baseline_score=70.0,
    )

    assert first == second


def test_baseline_score_is_validated(tmp_path):
    store = make_store(tmp_path)
    persist_property_history(store)

    try:
        make_generator(store).recent(
            baseline_score=101.0,
        )
    except ValueError as exc:
        assert "baseline_score" in str(exc)
    else:
        raise AssertionError("expected ValueError")
