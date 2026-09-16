from experience.historical_learning import (
    HistoricalLearningRetriever,
)
from experience.historical_learning_injection import (
    HistoricalLearningInjector,
)
from experience.learning_persistence import (
    LearningPersistenceBridge,
)
from experience.learning_signal import (
    LearningSignalCollector,
)
from experience.store import ExperienceStore


def make_store(tmp_path):
    return ExperienceStore(
        str(tmp_path / "learning.db")
    )


def test_recent_injects_persisted_learning(tmp_path):
    store = make_store(tmp_path)
    collector = LearningSignalCollector()

    signal = collector.repair_success(
        "fix add",
        strategy="property",
        score=95.0,
    )

    LearningPersistenceBridge(store).persist([signal])

    injector = HistoricalLearningInjector(
        HistoricalLearningRetriever(store)
    )

    result = injector.recent()

    assert result.retrieved == 1
    assert len(result.signals) == 1
    assert result.signals[0].strategy == "property"
    assert result.utility_by_strategy["property"] == 95.0


def test_multiple_scores_average_per_strategy(tmp_path):
    store = make_store(tmp_path)
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
            score=80.0,
        ),
        collector.repair_success(
            "c",
            strategy="standard",
            score=70.0,
        ),
    ]

    LearningPersistenceBridge(store).persist(signals)

    result = HistoricalLearningInjector(
        HistoricalLearningRetriever(store)
    ).recent()

    assert result.utility_by_strategy["property"] == 85.0
    assert result.utility_by_strategy["standard"] == 70.0


def test_strategy_names_are_normalized(tmp_path):
    store = make_store(tmp_path)
    collector = LearningSignalCollector()

    signal = collector.repair_success(
        "fix",
        strategy="  PROPERTY  ",
        score=90.0,
    )

    LearningPersistenceBridge(store).persist([signal])

    result = HistoricalLearningInjector(
        HistoricalLearningRetriever(store)
    ).recent()

    assert "property" in result.utility_by_strategy


def test_empty_history_is_safe(tmp_path):
    result = HistoricalLearningInjector(
        HistoricalLearningRetriever(make_store(tmp_path))
    ).recent()

    assert result.retrieved == 0
    assert result.signals == ()
    assert result.utility_by_strategy == {}


def test_search_injects_matching_history(tmp_path):
    store = make_store(tmp_path)
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix parser",
            strategy="mutation",
            score=92.0,
        ),
        collector.repair_success(
            "fix database",
            strategy="standard",
            score=80.0,
        ),
    ]

    LearningPersistenceBridge(store).persist(signals)

    result = HistoricalLearningInjector(
        HistoricalLearningRetriever(store)
    ).search("parser")

    assert result.retrieved == 1
    assert result.signals[0].task == "fix parser"
    assert result.utility_by_strategy == {"mutation": 92.0}


def test_archived_history_is_not_injected(tmp_path):
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

    result = HistoricalLearningInjector(
        HistoricalLearningRetriever(store)
    ).recent()

    assert result.retrieved == 0
    assert result.utility_by_strategy == {}


def test_retriever_is_kept_as_dependency(tmp_path):
    store = make_store(tmp_path)
    retriever = HistoricalLearningRetriever(store)
    injector = HistoricalLearningInjector(retriever)

    assert injector.retriever is retriever


def test_scores_are_not_clamped_again():
    from experience.learning_signal import LearningSignal

    class FakeRetriever:
        def recent(self, limit=20):
            class Result:
                signals = (
                    LearningSignal(
                        signal_type=__import__(
                            "experience.learning_signal",
                            fromlist=["LearningSignalType"],
                        ).LearningSignalType.REPAIR_SUCCESS,
                        task="fix",
                        strategy="property",
                        attempts=1,
                        score=100.0,
                    ),
                )

            return Result()

        def search(self, query, limit=10):
            return self.recent(limit)

    result = HistoricalLearningInjector(
        FakeRetriever()
    ).recent()

    assert result.utility_by_strategy["property"] == 100.0


def test_injection_is_deterministic(tmp_path):
    store = make_store(tmp_path)
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=90.0 + index,
        )
        for index in range(3)
    ]

    LearningPersistenceBridge(store).persist(signals)

    injector = HistoricalLearningInjector(
        HistoricalLearningRetriever(store)
    )

    first = injector.recent()
    second = injector.recent()

    assert first == second
