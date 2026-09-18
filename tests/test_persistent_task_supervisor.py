import pytest

from core.persistent_task_supervisor import (
    PersistentTaskSupervisor,
)
from core.runtime_state import RuntimeStateStore
from core.task_supervisor import TaskSupervisor


def make_supervisor(tmp_path, max_attempts=3):
    store = RuntimeStateStore(
        tmp_path / "runtime.db"
    )

    supervisor = PersistentTaskSupervisor(
        store=store,
        supervisor=TaskSupervisor(
            max_attempts=max_attempts,
        ),
    )

    return supervisor, store


def test_new_persistent_supervisor_starts_empty(tmp_path):
    supervisor, store = make_supervisor(tmp_path)

    assert supervisor.all() == ()
    assert store.value(supervisor.KEY) is None


def test_task_creation_is_persisted(tmp_path):
    supervisor, store = make_supervisor(tmp_path)

    result = supervisor.create("task-1")

    assert result.status == "created"
    assert store.value(supervisor.KEY) is not None


def test_task_survives_new_supervisor_instance(tmp_path):
    path = tmp_path / "runtime.db"

    first_store = RuntimeStateStore(path)
    first = PersistentTaskSupervisor(
        store=first_store,
    )

    first.create("task-1")
    first.start("task-1")
    first.complete("task-1")

    second_store = RuntimeStateStore(path)
    second = PersistentTaskSupervisor(
        store=second_store,
    )

    result = second.get("task-1")

    assert result is not None
    assert result.task_id == "task-1"
    assert result.status == "completed"
    assert result.attempt == 1
    assert result.success is True


def test_intermediate_retry_state_is_persisted(tmp_path):
    supervisor, _ = make_supervisor(tmp_path)

    supervisor.create("task-1")
    supervisor.start("task-1")

    result = supervisor.retry(
        "task-1",
        "verification failed",
    )

    restarted = PersistentTaskSupervisor(
        store=RuntimeStateStore(
            supervisor.store.db_path
        ),
    )

    persisted = restarted.get("task-1")

    assert result.status == "retrying"
    assert persisted is not None
    assert persisted.status == "retrying"
    assert persisted.attempt == 1
    assert persisted.reason == "verification failed"


def test_failed_task_is_persisted(tmp_path):
    supervisor, _ = make_supervisor(tmp_path)

    supervisor.create("task-1")
    supervisor.start("task-1")
    supervisor.fail(
        "task-1",
        "agent failed",
    )

    restarted = PersistentTaskSupervisor(
        store=RuntimeStateStore(
            supervisor.store.db_path
        ),
    )

    result = restarted.get("task-1")

    assert result is not None
    assert result.status == "failed"
    assert result.success is False
    assert result.reason == "agent failed"


def test_stopped_task_is_persisted(tmp_path):
    supervisor, _ = make_supervisor(tmp_path)

    supervisor.create("task-1")

    supervisor.stop(
        "task-1",
        "user stopped task",
    )

    restarted = PersistentTaskSupervisor(
        store=RuntimeStateStore(
            supervisor.store.db_path
        ),
    )

    result = restarted.get("task-1")

    assert result is not None
    assert result.status == "stopped"
    assert result.success is False


def test_multiple_tasks_survive_restart(tmp_path):
    supervisor, _ = make_supervisor(tmp_path)

    supervisor.create("task-b")
    supervisor.start("task-b")
    supervisor.complete("task-b")

    supervisor.create("task-a")
    supervisor.start("task-a")
    supervisor.fail("task-a", "failed")

    restarted = PersistentTaskSupervisor(
        store=RuntimeStateStore(
            supervisor.store.db_path
        ),
    )

    assert [item.task_id for item in restarted.all()] == [
        "task-a",
        "task-b",
    ]


def test_clear_removes_persisted_tasks(tmp_path):
    supervisor, store = make_supervisor(tmp_path)

    supervisor.create("task-1")
    supervisor.clear()

    assert supervisor.all() == ()
    assert store.value(supervisor.KEY) is None


def test_invalid_persisted_json_is_rejected(tmp_path):
    store = RuntimeStateStore(
        tmp_path / "runtime.db"
    )

    store.set(
        PersistentTaskSupervisor.KEY,
        "{broken",
    )

    with pytest.raises(
        RuntimeError,
        match="invalid persisted task supervision state",
    ):
        PersistentTaskSupervisor(
            store=store,
        )


def test_invalid_persisted_version_is_rejected(tmp_path):
    store = RuntimeStateStore(
        tmp_path / "runtime.db"
    )

    store.set(
        PersistentTaskSupervisor.KEY,
        '{"version":999,"tasks":[]}',
    )

    with pytest.raises(
        RuntimeError,
        match="unsupported persisted task supervision version",
    ):
        PersistentTaskSupervisor(
            store=store,
        )


def test_invalid_persisted_task_list_is_rejected(tmp_path):
    store = RuntimeStateStore(
        tmp_path / "runtime.db"
    )

    store.set(
        PersistentTaskSupervisor.KEY,
        '{"version":1,"tasks":"broken"}',
    )

    with pytest.raises(
        RuntimeError,
        match="persisted task supervision tasks must be a list",
    ):
        PersistentTaskSupervisor(
            store=store,
        )


def test_invalid_persisted_task_entry_is_rejected(tmp_path):
    store = RuntimeStateStore(
        tmp_path / "runtime.db"
    )

    store.set(
        PersistentTaskSupervisor.KEY,
        '{"version":1,"tasks":[{"task_id":"task-1"}]}',
    )

    with pytest.raises(
        RuntimeError,
        match="invalid persisted task execution values",
    ):
        PersistentTaskSupervisor(
            store=store,
        )


def test_task_attempt_limits_survive_restart(tmp_path):
    path = tmp_path / "runtime.db"

    first = PersistentTaskSupervisor(
        store=RuntimeStateStore(path),
        supervisor=TaskSupervisor(
            max_attempts=2,
        ),
    )

    first.create("task-1")
    first.start("task-1")
    first.retry(
        "task-1",
        "retry",
    )

    second = PersistentTaskSupervisor(
        store=RuntimeStateStore(path),
        supervisor=TaskSupervisor(
            max_attempts=2,
        ),
    )

    running = second.start("task-1")

    assert running.attempt == 2

    failed = second.retry(
        "task-1",
        "retry again",
    )

    assert failed.status == "failed"


def test_persistence_uses_existing_runtime_store(tmp_path):
    store = RuntimeStateStore(
        tmp_path / "runtime.db"
    )

    supervisor = PersistentTaskSupervisor(
        store=store,
    )

    supervisor.create("task-1")

    assert store.value(
        PersistentTaskSupervisor.KEY
    ) is not None
