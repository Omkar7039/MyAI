from experience.automatic_learning_persistence import (
    AutomaticLearningPersistence,
)
from experience.learning_persistence import (
    LearningPersistenceBridge,
)
from experience.outcome_capture import AutomaticOutcomeCapture
from experience.store import ExperienceStore


def make_store(tmp_path):
    return ExperienceStore(
        str(tmp_path / "learning.db")
    )


def capture_success():
    return AutomaticOutcomeCapture().capture(
        task="fix add",
        strategy="property",
        repair_success=True,
        verification_success=True,
        repair_score=95.0,
        verification_score=90.0,
    )


def test_captured_outcome_is_persisted(tmp_path):
    store = make_store(tmp_path)

    captured = capture_success()

    result = AutomaticLearningPersistence(store).persist(
        captured
    )

    assert result.persisted is True
    assert result.persistence.persisted == 2
    assert result.persistence.skipped == 0
    assert len(result.persistence.experience_ids) == 2


def test_persisted_records_can_be_loaded(tmp_path):
    store = make_store(tmp_path)
    captured = capture_success()

    result = AutomaticLearningPersistence(store).persist(
        captured
    )

    for experience_id in result.persistence.experience_ids:
        loaded = store.get(experience_id)

        assert loaded is not None
        assert loaded.category == "learning"


def test_duplicate_capture_is_skipped(tmp_path):
    store = make_store(tmp_path)
    captured = capture_success()
    persistence = AutomaticLearningPersistence(store)

    first = persistence.persist(captured)
    second = persistence.persist(captured)

    assert first.persistence.persisted == 2
    assert second.persistence.persisted == 0
    assert second.persistence.skipped == 2
    assert second.persistence.experience_ids == (
        first.persistence.experience_ids
    )


def test_failed_outcome_is_persisted(tmp_path):
    store = make_store(tmp_path)

    captured = AutomaticOutcomeCapture().capture(
        task="fix parser",
        strategy="standard",
        repair_success=False,
        verification_success=False,
    )

    result = AutomaticLearningPersistence(store).persist(
        captured
    )

    assert result.persisted is True
    assert result.persistence.persisted == 2


def test_retry_and_rollback_are_persisted(tmp_path):
    store = make_store(tmp_path)

    captured = AutomaticOutcomeCapture().capture(
        task="recover",
        strategy="multifile",
        repair_success=False,
        verification_success=False,
        attempts=3,
        retried=True,
        rolled_back=True,
    )

    result = AutomaticLearningPersistence(store).persist(
        captured
    )

    assert result.persistence.persisted == 4


def test_custom_bridge_is_respected(tmp_path):
    class FixedBridge(LearningPersistenceBridge):
        def __init__(self):
            pass

        def persist(self, signals):
            from experience.learning_persistence import (
                LearningPersistenceResult,
            )

            return LearningPersistenceResult(
                persisted=99,
                skipped=0,
                experience_ids=("fixed",),
            )

    store = make_store(tmp_path)
    captured = capture_success()

    result = AutomaticLearningPersistence(
        store,
        persistence_bridge=FixedBridge(),
    ).persist(captured)

    assert result.persisted is True
    assert result.persistence.persisted == 99
    assert result.persistence.experience_ids == ("fixed",)


def test_false_captured_outcome_is_not_persisted(tmp_path):
    captured = capture_success()

    captured = type(captured)(
        task=captured.task,
        strategy=captured.strategy,
        feedback=captured.feedback,
        captured=False,
    )

    result = AutomaticLearningPersistence(
        make_store(tmp_path)
    ).persist(captured)

    assert result.persisted is False
    assert result.persistence.persisted == 0
    assert result.persistence.skipped == 0
    assert result.persistence.experience_ids == ()


def test_empty_feedback_signals_are_safe(tmp_path):
    from experience.learning_feedback import (
        LearningFeedback,
    )
    from experience.outcome_capture import CapturedOutcome

    feedback = LearningFeedback(
        signals=(),
        repair_success=True,
        verification_success=True,
        strategy="standard",
        score=100.0,
    )

    captured = CapturedOutcome(
        task="empty",
        strategy="standard",
        feedback=feedback,
        captured=True,
    )

    result = AutomaticLearningPersistence(
        make_store(tmp_path)
    ).persist(captured)

    assert result.persisted is False
    assert result.persistence.persisted == 0


def test_persistence_is_deterministic(tmp_path):
    store = make_store(tmp_path)
    captured = capture_success()
    persistence = AutomaticLearningPersistence(store)

    first = persistence.persist(captured)
    second = persistence.persist(captured)

    assert first.persistence.experience_ids == (
        second.persistence.experience_ids
    )
    assert second.persistence.skipped == 2


def test_existing_persistence_bridge_semantics_are_preserved(
    tmp_path,
):
    store = make_store(tmp_path)
    captured = capture_success()

    result = AutomaticLearningPersistence(store).persist(
        captured
    )

    direct_ids = tuple(
        result.persistence.experience_ids
    )

    for experience_id in direct_ids:
        loaded = store.get(experience_id)
        assert loaded is not None
        assert loaded.lifecycle_state == "active"
