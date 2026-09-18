from core.persistent_task_supervisor import PersistentTaskSupervisor
from core.runtime_recovery_controller import RuntimeRecoveryController
from core.runtime_state import RuntimeStateStore
from core.supervised_task_runner import SupervisedTaskRunner
from core.task_retention import TaskRetentionManager


def test_production_task_supervision_e2e(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    store_path = tmp_path / "runtime_state.db"
    store = RuntimeStateStore(store_path)
    supervisor = PersistentTaskSupervisor(store=store)
    recovery_controller = RuntimeRecoveryController()
    runner = SupervisedTaskRunner(
        supervisor=supervisor,
        recovery_controller=recovery_controller,
    )

    success = runner.run(
        task_id="e2e-success",
        execute=lambda: "ok",
        fingerprint="e2e:success",
    )
    assert success.response == "ok"
    assert success.task.status == "completed"
    assert success.task.success is True

    recovered = runner.run(
        task_id="e2e-recovery",
        execute=lambda: (_ for _ in ()).throw(
            ValueError("malformed state detected")
        ),
        fingerprint="e2e:recovery",
        recover=lambda: True,
    )
    assert recovered.response is None
    assert recovered.recovery is not None
    assert recovered.recovery.recovered is True
    assert recovered.recovery.action == "continue"
    assert recovered.task.status == "completed"
    assert recovered.task.success is True

    restarted_store = RuntimeStateStore(store_path)
    restarted = PersistentTaskSupervisor(store=restarted_store)

    restored = {task.task_id: task for task in restarted.all()}
    assert set(restored) == {"e2e-success", "e2e-recovery"}
    assert all(task.status == "completed" for task in restored.values())

    retention = TaskRetentionManager(restarted, max_terminal_tasks=1)

    preview = retention.run(apply=False)
    assert preview.existing_terminal_tasks == 2
    assert preview.retained_terminal_tasks == 1
    assert preview.pruned_terminal_tasks == 1
    assert preview.active_tasks == 0

    applied = retention.run(apply=True)
    assert applied.applied is True
    assert applied.pruned_terminal_tasks == 1

    final_store = RuntimeStateStore(store_path)
    final_supervisor = PersistentTaskSupervisor(store=final_store)
    final_tasks = final_supervisor.all()

    assert len(final_tasks) == 1
    assert final_tasks[0].status == "completed"
