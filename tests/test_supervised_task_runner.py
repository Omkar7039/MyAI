import pytest

from core.runtime_recovery import (
    RuntimeRecoveryDecisionEngine,
)
from core.runtime_recovery_audit import RuntimeRecoveryAudit
from core.runtime_recovery_controller import (
    RuntimeRecoveryController,
)
from core.runtime_recovery_guard import RuntimeRecoveryGuard
from core.runtime_recovery_throttle import (
    RuntimeRecoveryThrottle,
)
from core.runtime_failure import RuntimeFailureClassifier
from core.supervised_task_runner import (
    SupervisedTaskResult,
    SupervisedTaskRunner,
)
from core.task_supervisor import TaskSupervisor


def make_runner(tmp_path, *, max_attempts=3):
    audit = RuntimeRecoveryAudit(
        tmp_path / "recovery_audit.db"
    )

    controller = RuntimeRecoveryController(
        classifier=RuntimeFailureClassifier(),
        decision_engine=RuntimeRecoveryDecisionEngine(),
        guard=RuntimeRecoveryGuard(
            max_attempts=max_attempts,
        ),
        throttle=RuntimeRecoveryThrottle(
            cooldown_seconds=0,
        ),
        audit=audit,
    )

    return (
        SupervisedTaskRunner(
            supervisor=TaskSupervisor(
                max_attempts=max_attempts,
            ),
            recovery_controller=controller,
        ),
        audit,
    )


def test_successful_task_completes(tmp_path):
    runner, audit = make_runner(tmp_path)

    result = runner.run(
        task_id="task-1",
        execute=lambda: "success",
        fingerprint="task-1",
    )

    assert isinstance(result, SupervisedTaskResult)
    assert result.response == "success"
    assert result.task.status == "completed"
    assert result.task.success is True
    assert result.task.attempt == 1
    assert result.recovery is None
    assert audit.count() == 0


def test_unknown_failure_stops_task(tmp_path):
    runner, audit = make_runner(tmp_path)

    def execute():
        raise RuntimeError("unexpected")

    result = runner.run(
        task_id="task-2",
        execute=execute,
        fingerprint="task-2",
    )

    assert result.response is None
    assert result.task.status == "failed"
    assert result.task.success is False
    assert result.recovery is not None
    assert result.recovery.action == "stop"
    assert audit.count() >= 1


def test_state_failure_can_recover_and_complete(tmp_path):
    runner, audit = make_runner(tmp_path)

    calls = []

    def execute():
        calls.append(True)
        raise ValueError("malformed state detected")

    def recover():
        return True

    result = runner.run(
        task_id="task-state",
        execute=execute,
        fingerprint="state:task",
        recover=recover,
    )

    assert calls == [True]
    assert result.task.status == "completed"
    assert result.task.success is True
    assert result.recovery is not None
    assert result.recovery.recovered is True
    assert result.recovery.action == "continue"
    assert audit.count() >= 3


def test_runtime_failure_can_recover_and_complete(tmp_path):
    runner, audit = make_runner(tmp_path)

    def execute():
        raise RuntimeError("runtime startup failed")

    result = runner.run(
        task_id="task-runtime",
        execute=execute,
        fingerprint="runtime:task",
        recover=lambda: True,
    )

    assert result.task.status == "completed"
    assert result.task.success is True
    assert result.recovery is not None
    assert result.recovery.recovered is True


def test_recovery_failure_stops_task(tmp_path):
    runner, audit = make_runner(tmp_path)

    result = runner.run(
        task_id="task-fail-recovery",
        execute=lambda: (_ for _ in ()).throw(
            RuntimeError("runtime startup failed")
        ),
        fingerprint="runtime:task",
        recover=lambda: False,
    )

    assert result.task.status == "failed"
    assert result.task.success is False
    assert result.recovery.action == "stop"


def test_task_retry_budget_is_respected(tmp_path):
    runner, audit = make_runner(
        tmp_path,
        max_attempts=2,
    )

    calls = []

    def execute():
        calls.append(True)
        raise TimeoutError("timed out")

    result = runner.run(
        task_id="task-timeout",
        execute=execute,
        fingerprint="timeout:task",
        max_task_retries=1,
    )

    assert len(calls) <= 2
    assert result.task.status == "failed"
    assert result.task.success is False
    assert result.recovery.action == "retry"


def test_recovery_executor_exception_stops_task(tmp_path):
    runner, audit = make_runner(tmp_path)

    def recover():
        raise RuntimeError("recovery exploded")

    result = runner.run(
        task_id="task-recovery-exception",
        execute=lambda: (_ for _ in ()).throw(
            RuntimeError("runtime startup failed")
        ),
        fingerprint="runtime:task",
        recover=recover,
    )

    assert result.task.status == "failed"
    assert result.recovery.action == "stop"
    assert "recovery exploded" in result.recovery.reason


def test_max_task_retries_negative_is_rejected(tmp_path):
    runner, _ = make_runner(tmp_path)

    with pytest.raises(
        ValueError,
        match="max_task_retries must be >= 0",
    ):
        runner.run(
            task_id="task-invalid",
            execute=lambda: "ok",
            fingerprint="task-invalid",
            max_task_retries=-1,
        )


def test_retry_path_reaches_second_execution(tmp_path):
    runner, _ = make_runner(
        tmp_path,
        max_attempts=3,
    )

    calls = []

    def execute():
        calls.append(len(calls) + 1)

        if len(calls) == 1:
            raise TimeoutError("first timeout")

        return "recovered by retry"

    result = runner.run(
        task_id="task-retry",
        execute=execute,
        fingerprint="timeout:task-retry",
        max_task_retries=2,
    )

    assert calls == [1, 2]
    assert result.response == "recovered by retry"
    assert result.task.status == "completed"
    assert result.task.attempt == 2


def test_task_id_is_required_by_supervisor(tmp_path):
    runner, _ = make_runner(tmp_path)

    with pytest.raises(ValueError):
        runner.run(
            task_id=" ",
            execute=lambda: "ok",
            fingerprint="task-invalid",
        )
