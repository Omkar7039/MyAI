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


def test_persists_learning_signal(tmp_path):
    collector = LearningSignalCollector()
    signal = collector.repair_success(
        "fix add",
        strategy="property",
        attempts=1,
        score=95.0,
    )

    result = LearningPersistenceBridge(
        make_store(tmp_path)
    ).persist([signal])

    assert result.persisted == 1
    assert result.skipped == 0
    assert len(result.experience_ids) == 1

    experience = make_store(tmp_path)
    loaded = experience.get(result.experience_ids[0])

    assert loaded is not None
    assert loaded.category == "learning"
    assert loaded.task == "fix add"
    assert loaded.action == "repair_success"
    assert loaded.success is True


def test_duplicate_signal_is_skipped(tmp_path):
    collector = LearningSignalCollector()
    signal = collector.verification_success(
        "verify",
        strategy="property",
        score=90.0,
    )

    store = make_store(tmp_path)
    bridge = LearningPersistenceBridge(store)

    first = bridge.persist([signal])
    second = bridge.persist([signal])

    assert first.persisted == 1
    assert second.persisted == 0
    assert second.skipped == 1
    assert first.experience_ids == second.experience_ids


def test_multiple_signals_are_persisted(tmp_path):
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "repair",
            strategy="standard",
            score=80.0,
        ),
        collector.verification_success(
            "verify",
            strategy="standard",
            score=85.0,
        ),
        collector.retry(
            "retry",
            strategy="standard",
        ),
    ]

    result = LearningPersistenceBridge(
        make_store(tmp_path)
    ).persist(signals)

    assert result.persisted == 3
    assert result.skipped == 0
    assert len(set(result.experience_ids)) == 3


def test_failure_signal_is_persisted_as_unsuccessful(tmp_path):
    collector = LearningSignalCollector()
    signal = collector.repair_failure(
        "fix parser",
        strategy="standard",
    )

    store = make_store(tmp_path)
    result = LearningPersistenceBridge(store).persist([signal])

    loaded = store.get(result.experience_ids[0])

    assert loaded is not None
    assert loaded.success is False
    assert loaded.outcome == "repair_failure"


def test_strategy_is_preserved_in_metadata(tmp_path):
    collector = LearningSignalCollector()
    signal = collector.verification_success(
        "verify",
        strategy="mutation",
        attempts=2,
        score=92.0,
        metadata="benchmark",
    )

    store = make_store(tmp_path)
    result = LearningPersistenceBridge(store).persist([signal])

    loaded = store.get(result.experience_ids[0])

    assert loaded is not None
    assert "strategy=mutation" in loaded.metadata
    assert "attempts=2" in loaded.metadata
    assert "score=92.00" in loaded.metadata
    assert "source_metadata=benchmark" in loaded.metadata


def test_retry_signal_is_not_marked_successful(tmp_path):
    collector = LearningSignalCollector()
    signal = collector.retry(
        "repair",
        strategy="multifile",
    )

    store = make_store(tmp_path)
    result = LearningPersistenceBridge(store).persist([signal])

    loaded = store.get(result.experience_ids[0])

    assert loaded is not None
    assert loaded.success is False
    assert loaded.outcome == "retry"


def test_ids_are_deterministic(tmp_path):
    collector = LearningSignalCollector()
    signal = collector.repair_success(
        "fix",
        strategy="property",
        attempts=2,
        score=90.0,
    )

    bridge = LearningPersistenceBridge(
        make_store(tmp_path)
    )

    first = bridge._experience_id(signal)
    second = bridge._experience_id(signal)

    assert first == second
    assert first.startswith("learning-")


def test_different_signals_have_different_ids(tmp_path):
    collector = LearningSignalCollector()

    first = collector.repair_success(
        "fix",
        strategy="property",
        score=90.0,
    )
    second = collector.repair_success(
        "fix",
        strategy="standard",
        score=90.0,
    )

    bridge = LearningPersistenceBridge(
        make_store(tmp_path)
    )

    assert bridge._experience_id(first) != (
        bridge._experience_id(second)
    )


def test_empty_signal_list_is_safe(tmp_path):
    result = LearningPersistenceBridge(
        make_store(tmp_path)
    ).persist([])

    assert result.persisted == 0
    assert result.skipped == 0
    assert result.experience_ids == ()


def test_persistence_is_deterministic(tmp_path):
    collector = LearningSignalCollector()
    signal = collector.verification_success(
        "verify",
        strategy="property",
        score=90.0,
    )

    first_store = make_store(tmp_path / "a")
    second_store = make_store(tmp_path / "b")

    first = LearningPersistenceBridge(
        first_store
    ).persist([signal])
    second = LearningPersistenceBridge(
        second_store
    ).persist([signal])

    assert first == second
