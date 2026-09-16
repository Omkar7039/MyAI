from experience.historical_learning import (
    HistoricalLearningRetriever,
)
from experience.learning_persistence import (
    LearningPersistenceBridge,
)
from experience.learning_signal import (
    LearningSignalCollector,
    LearningSignalType,
)
from experience.store import ExperienceStore


def make_store(tmp_path):
    return ExperienceStore(
        str(tmp_path / "experiences.db")
    )


def test_recent_retrieves_persisted_learning_signal(tmp_path):
    store = make_store(tmp_path)
    collector = LearningSignalCollector()

    signal = collector.repair_success(
        "fix add",
        strategy="property",
        attempts=2,
        score=95.0,
    )

    LearningPersistenceBridge(store).persist([signal])

    result = HistoricalLearningRetriever(store).recent()

    assert result.retrieved == 1
    assert len(result.signals) == 1
    assert result.source_experience_ids
    assert result.signals[0].signal_type == (
        LearningSignalType.REPAIR_SUCCESS
    )
    assert result.signals[0].task == "fix add"
    assert result.signals[0].strategy == "property"
    assert result.signals[0].attempts == 2
    assert result.signals[0].score == 95.0


def test_search_retrieves_matching_learning(tmp_path):
    store = make_store(tmp_path)
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix parser",
            strategy="mutation",
            score=90.0,
        ),
        collector.repair_success(
            "fix database",
            strategy="standard",
            score=80.0,
        ),
    ]

    LearningPersistenceBridge(store).persist(signals)

    result = HistoricalLearningRetriever(store).search(
        "parser"
    )

    assert result.retrieved == 1
    assert result.signals[0].task == "fix parser"


def test_get_returns_learning_signal(tmp_path):
    store = make_store(tmp_path)
    collector = LearningSignalCollector()

    signal = collector.verification_success(
        "verify",
        strategy="property",
        score=88.0,
    )

    persisted = LearningPersistenceBridge(store).persist(
        [signal]
    )

    result = HistoricalLearningRetriever(store).get(
        persisted.experience_ids[0]
    )

    assert result is not None
    assert result.signal_type == (
        LearningSignalType.VERIFICATION_SUCCESS
    )
    assert result.strategy == "property"
    assert result.score == 88.0


def test_non_learning_experience_is_ignored(tmp_path):
    store = make_store(tmp_path)

    from experience.store import Experience

    experience = Experience(
        experience_id="normal-1",
        task="ordinary task",
        category="repair",
        action="repair",
        outcome="success",
        success=True,
        lesson="ordinary experience",
        metadata="",
    )

    store.add(experience)

    retriever = HistoricalLearningRetriever(store)

    assert retriever.get("normal-1") is None
    assert retriever.recent().signals == ()


def test_archived_learning_experience_is_ignored(tmp_path):
    store = make_store(tmp_path)
    collector = LearningSignalCollector()

    signal = collector.repair_success(
        "archived",
        strategy="property",
        score=90.0,
    )

    persisted = LearningPersistenceBridge(store).persist(
        [signal]
    )

    store.archive(persisted.experience_ids[0])

    retriever = HistoricalLearningRetriever(store)

    assert retriever.get(
        persisted.experience_ids[0]
    ) is None
    assert retriever.recent().signals == ()


def test_invalid_learning_action_is_ignored(tmp_path):
    store = make_store(tmp_path)

    from experience.store import Experience

    experience = Experience(
        experience_id="learning-invalid",
        task="invalid",
        category="learning",
        action="unknown_signal",
        outcome="unknown",
        success=False,
        lesson="invalid",
        metadata="strategy=standard; attempts=1; score=0",
    )

    store.add(experience)

    result = HistoricalLearningRetriever(store).recent()

    assert result.retrieved == 0
    assert result.signals == ()


def test_metadata_is_reconstructed(tmp_path):
    store = make_store(tmp_path)
    collector = LearningSignalCollector()

    signal = collector.retry(
        "retry repair",
        strategy="multifile",
        attempts=3,
        score=42.0,
        metadata="source=test",
    )

    persisted = LearningPersistenceBridge(store).persist(
        [signal]
    )

    restored = HistoricalLearningRetriever(store).get(
        persisted.experience_ids[0]
    )

    assert restored is not None
    assert restored.signal_type == LearningSignalType.RETRY
    assert restored.strategy == "multifile"
    assert restored.attempts == 3
    assert restored.score == 42.0
    assert "source_metadata=source=test" in restored.metadata


def test_limit_is_respected(tmp_path):
    store = make_store(tmp_path)
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=90.0,
        )
        for index in range(5)
    ]

    LearningPersistenceBridge(store).persist(signals)

    result = HistoricalLearningRetriever(store).recent(
        limit=2
    )

    assert result.retrieved == 2
    assert len(result.signals) == 2


def test_empty_search_returns_no_learning(tmp_path):
    store = make_store(tmp_path)

    result = HistoricalLearningRetriever(store).search(
        "does-not-exist"
    )

    assert result.retrieved == 0
    assert result.signals == ()
    assert result.source_experience_ids == ()


def test_missing_id_returns_none(tmp_path):
    result = HistoricalLearningRetriever(
        make_store(tmp_path)
    ).get("missing")

    assert result is None


def test_retrieval_is_deterministic(tmp_path):
    store = make_store(tmp_path)
    collector = LearningSignalCollector()

    signal = collector.repair_success(
        "fix",
        strategy="property",
        score=90.0,
    )

    LearningPersistenceBridge(store).persist([signal])

    retriever = HistoricalLearningRetriever(store)

    first = retriever.recent()
    second = retriever.recent()

    assert first == second
