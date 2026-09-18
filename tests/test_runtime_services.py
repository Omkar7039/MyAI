from core.runtime_services import RuntimeServices
from core.runtime_state import RuntimeStateStore


def test_runtime_services_share_one_runtime_store(tmp_path):
    store = RuntimeStateStore(tmp_path / "runtime_state.db")

    services = RuntimeServices.create(
        store,
        max_rollback_entries=5,
    )

    assert services.store is store
    assert services.learning_state.store is store
    assert services.diagnostics.runtime_store is store
    assert services.diagnostics.learning_state is services.learning_state
    assert services.retention.state is services.learning_state


def test_runtime_services_default_components_are_constructed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    services = RuntimeServices.create(
        max_rollback_entries=3,
    )

    assert isinstance(services.store, RuntimeStateStore)
    assert services.retention.max_rollback_entries == 3


def test_runtime_services_reuses_persisted_learning_state(tmp_path):
    store = RuntimeStateStore(tmp_path / "runtime_state.db")

    first = RuntimeServices.create(store)

    second = RuntimeServices.create(store)

    assert first.learning_state is not second.learning_state
    assert first.diagnostics.learning_state is first.learning_state
    assert second.diagnostics.learning_state is second.learning_state
    assert first.store is second.store


def test_runtime_services_recovers_malformed_learning_state(tmp_path):
    store = RuntimeStateStore(tmp_path / "runtime_state.db")
    services = RuntimeServices.create(store)

    store.set(
        services.learning_state.KEY,
        '{"version":2,"changes":"broken","history":{}}',
    )

    result = services.recover_learning_state_if_needed()

    assert result is not None
    assert result.recovered is True
    assert result.state_name == "learning"
    assert result.quarantined_key is not None

    assert store.value(services.learning_state.KEY) is None
    assert store.value(result.quarantined_key) == (
        '{"version":2,"changes":"broken","history":{}}'
    )


def test_runtime_services_leaves_valid_learning_state_untouched(
    tmp_path,
):
    store = RuntimeStateStore(tmp_path / "runtime_state.db")
    services = RuntimeServices.create(store)

    raw = (
        '{"version":2,"changes":[],"history":{}}'
    )
    store.set(
        services.learning_state.KEY,
        raw,
    )

    result = services.recover_learning_state_if_needed()

    assert result is None
    assert store.value(services.learning_state.KEY) == raw


def test_runtime_services_recovery_precedes_retention(tmp_path):
    store = RuntimeStateStore(tmp_path / "runtime_state.db")
    services = RuntimeServices.create(
        store,
        max_rollback_entries=1,
    )

    store.set(
        services.learning_state.KEY,
        '{"version":2,"changes":"broken","history":{}}',
    )

    recovery = services.recover_learning_state_if_needed()

    assert recovery is not None
    assert recovery.recovered is True

    report = services.retention.run(apply=True)

    assert report.scanned_strategies == 0
    assert report.pruned_entries == 0
    assert report.retained_entries == 0


def test_runtime_services_readiness_is_true_for_healthy_runtime(
    tmp_path,
):
    store = RuntimeStateStore(tmp_path / "runtime_state.db")
    services = RuntimeServices.create(store)

    result = services.check_readiness()

    assert result.ready is True
    assert result.diagnostics.healthy is True
    assert result.diagnostics.issues == ()


def test_runtime_services_readiness_is_false_for_corrupted_learning_state(
    tmp_path,
):
    store = RuntimeStateStore(tmp_path / "runtime_state.db")
    services = RuntimeServices.create(store)

    store.set(
        services.learning_state.KEY,
        '{"version":2,"changes":"broken","history":{}}',
    )

    result = services.check_readiness()

    assert result.ready is False
    assert result.diagnostics.healthy is False
    assert any(
        "learning state unavailable" in issue
        for issue in result.diagnostics.issues
    )


def test_runtime_services_readiness_is_read_only(tmp_path):
    store = RuntimeStateStore(tmp_path / "runtime_state.db")
    services = RuntimeServices.create(store)

    store.set(
        "runtime.status",
        "ready",
    )

    before = store.all()

    result = services.check_readiness()

    after = store.all()

    assert result.ready is True
    assert before == after


def test_runtime_status_snapshot_reports_current_runtime_state(
    tmp_path,
):
    store = RuntimeStateStore(tmp_path / "runtime_state.db")
    services = RuntimeServices.create(store)

    store.set("runtime.status", "ready")
    store.set("runtime.clean_shutdown", "false")
    store.set("runtime.last_exit_code", "")

    snapshot = services.status_snapshot()

    assert snapshot.status == "ready"
    assert snapshot.healthy is True
    assert snapshot.active_strategy_count == 0
    assert snapshot.active_strategies == ()
    assert snapshot.rollback_available == ()
    assert snapshot.clean_shutdown is False
    assert snapshot.last_exit_code is None
    assert snapshot.issues == ()


def test_runtime_status_snapshot_reflects_learning_state(
    tmp_path,
):
    store = RuntimeStateStore(tmp_path / "runtime_state.db")
    services = RuntimeServices.create(store)

    store.set("runtime.status", "ready")

    snapshot = services.status_snapshot()

    assert snapshot.active_strategy_count == 0
    assert snapshot.active_strategies == ()
    assert snapshot.rollback_available == ()


def test_runtime_status_snapshot_is_read_only(tmp_path):
    store = RuntimeStateStore(tmp_path / "runtime_state.db")
    services = RuntimeServices.create(store)

    store.set("runtime.status", "ready")

    before = store.all()
    services.status_snapshot()
    after = store.all()

    assert before == after


def test_preview_learning_retention_does_not_modify_state(tmp_path):
    store = RuntimeStateStore(tmp_path / "runtime_state.db")
    services = RuntimeServices.create(
        store,
        max_rollback_entries=1,
    )

    before = store.all()

    report = services.preview_learning_retention()

    after = store.all()

    assert report.applied is False
    assert before == after


def test_apply_learning_retention_applies_configured_policy(tmp_path):
    store = RuntimeStateStore(tmp_path / "runtime_state.db")
    services = RuntimeServices.create(
        store,
        max_rollback_entries=1,
    )

    state = services.learning_state

    from experience.learning_state import LearningAppliedChange

    change_1 = LearningAppliedChange(
        strategy="property",
        previous_score=None,
        applied_score=80.0,
        observations=5,
        confidence=70.0,
    )
    change_2 = LearningAppliedChange(
        strategy="property",
        previous_score=80.0,
        applied_score=90.0,
        observations=5,
        confidence=75.0,
    )

    state.save(
        (change_2,),
        {
            "property": [
                change_1,
                change_2,
            ],
        },
    )

    report = services.apply_learning_retention()

    assert report.applied is True
    assert report.pruned_entries == 1
    assert report.retained_entries == 1

    _, history = state.load_with_history()

    assert len(history["property"]) == 1
    assert history["property"][0].applied_score == 90.0


def test_runtime_exit_code_recovery_happens_before_startup(tmp_path):
    store = RuntimeStateStore(tmp_path / "runtime.db")
    services = RuntimeServices.create(store)

    store.set(
        "runtime.last_exit_code",
        "not-an-exit-code",
    )

    result = services.recover_runtime_exit_code_if_needed()

    assert result is not None
    assert result.recovered is True
    assert result.state_name == "runtime.last_exit_code"
    assert result.quarantined_key is not None

    assert store.value("runtime.last_exit_code") is None
    assert store.value(result.quarantined_key) == "not-an-exit-code"


def test_runtime_exit_code_recovery_ignores_valid_value(tmp_path):
    store = RuntimeStateStore(tmp_path / "runtime.db")
    services = RuntimeServices.create(store)

    store.set(
        "runtime.last_exit_code",
        "130",
    )

    before = store.all()

    result = services.recover_runtime_exit_code_if_needed()

    after = store.all()

    assert result is None
    assert before == after


def test_runtime_exit_code_recovery_ignores_empty_value(tmp_path):
    store = RuntimeStateStore(tmp_path / "runtime.db")
    services = RuntimeServices.create(store)

    store.set(
        "runtime.last_exit_code",
        "",
    )

    result = services.recover_runtime_exit_code_if_needed()

    assert result is None
    assert store.value("runtime.last_exit_code") == ""


def test_runtime_services_constructs_supervision_stack(tmp_path):
    from core.runtime_recovery_controller import RuntimeRecoveryController
    from core.supervised_task_runner import SupervisedTaskRunner
    from core.task_supervisor import TaskSupervisor

    store = RuntimeStateStore(tmp_path / "runtime.db")
    services = RuntimeServices.create(store)

    assert isinstance(
        services.task_supervisor,
        TaskSupervisor,
    )
    assert isinstance(
        services.recovery_controller,
        RuntimeRecoveryController,
    )
    assert isinstance(
        services.task_runner,
        SupervisedTaskRunner,
    )


def test_runtime_services_shares_supervisor_with_task_runner(
    tmp_path,
):
    store = RuntimeStateStore(tmp_path / "runtime.db")
    services = RuntimeServices.create(store)

    assert (
        services.task_runner.supervisor
        is services.task_supervisor
    )


def test_runtime_services_shares_recovery_controller_with_task_runner(
    tmp_path,
):
    store = RuntimeStateStore(tmp_path / "runtime.db")
    services = RuntimeServices.create(store)

    assert (
        services.task_runner.recovery_controller
        is services.recovery_controller
    )


def test_runtime_services_task_runner_executes_successful_task(
    tmp_path,
):
    store = RuntimeStateStore(tmp_path / "runtime.db")
    services = RuntimeServices.create(store)

    result = services.task_runner.run(
        task_id="service-task-1",
        execute=lambda: "service success",
        fingerprint="service-task-1",
    )

    assert result.response == "service success"
    assert result.task.status == "completed"
    assert result.task.success is True


def test_runtime_services_task_runner_handles_recoverable_failure(
    tmp_path,
):
    store = RuntimeStateStore(tmp_path / "runtime.db")
    services = RuntimeServices.create(store)

    result = services.task_runner.run(
        task_id="service-task-2",
        execute=lambda: (_ for _ in ()).throw(
            ValueError("malformed state detected")
        ),
        fingerprint="state:service-task-2",
        recover=lambda: True,
    )

    assert result.task.status == "completed"
    assert result.task.success is True
    assert result.recovery is not None
    assert result.recovery.recovered is True
