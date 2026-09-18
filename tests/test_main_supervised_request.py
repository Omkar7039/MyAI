from core.runtime_recovery_audit import RuntimeRecoveryAudit
from core.runtime_recovery_controller import RuntimeRecoveryController
from core.runtime_recovery_guard import RuntimeRecoveryGuard
from core.runtime_recovery_throttle import RuntimeRecoveryThrottle
from core.runtime_services import RuntimeServices
from core.task_supervisor import TaskSupervisor
from core.runtime_state import RuntimeStateStore


class FakeAI:
    def __init__(self, response="hello"):
        self.response = response
        self.calls = 0

    def handle(self, user_input):
        self.calls += 1
        return f"{self.response}: {user_input}"


class FailingAI:
    def handle(self, user_input):
        raise RuntimeError("request failed")


def make_services(tmp_path):
    return RuntimeServices.create(
        RuntimeStateStore(
            tmp_path / "runtime.db"
        )
    )



def test_supervised_request_returns_successful_task_result(
    tmp_path,
):
    from main import run_supervised_request
    from core.supervised_task_runner import SupervisedTaskRunner

    services = make_services(tmp_path)

    ai = FakeAI()

    result = run_supervised_request(
        ai,
        services,
        "hello",
    )

    assert result.task.status == "completed"
    assert result.task.success is True
    assert result.response == "hello: hello"
    assert ai.calls == 1


def test_supervised_request_reports_failed_task(
    tmp_path,
    capsys,
):
    from main import run_supervised_request
    from core.supervised_task_runner import SupervisedTaskRunner

    services = make_services(tmp_path)

    result = run_supervised_request(
        FailingAI(),
        services,
        "broken",
    )

    output = capsys.readouterr().out

    assert result.response is None
    assert result.task.status == "failed"
    assert result.task.success is False
    assert "Task" in output
    assert "failed" in output


def test_supervised_request_uses_shared_task_runner(
    tmp_path,
):
    from main import run_supervised_request
    from core.supervised_task_runner import SupervisedTaskRunner

    services = make_services(tmp_path)

    result = run_supervised_request(
        FakeAI(),
        services,
        "shared",
    )

    assert result.task.task_id.startswith("interactive-")
    assert services.task_supervisor.get(
        result.task.task_id
    ) == result.task
