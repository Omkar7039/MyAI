from agents.autonomous_multifile_repair import AutonomousMultiFileRepair
from agents.multifile_regression_validator import MultiFileRegressionValidator
from agents.multifile_reverification import MultiFileReverification
from agents.multifile_recovery import MultiFileRecoveryManager


class FakeExecutor:
    def __init__(self):
        self.calls = []

    def execute(self, request, project_root):
        self.calls.append(request)

        if len(self.calls) == 1:
            return {
                "success": False,
                "stage": "post_apply_verification",
                "errors": ["cross-file regression failed"],
                "rolled_back": True,
            }

        return {
            "success": True,
            "stage": "complete",
            "errors": [],
            "rolled_back": False,
        }


def test_full_autonomous_multifile_repair_end_to_end():
    executor = FakeExecutor()

    controller = AutonomousMultiFileRepair(
        executor,
        max_attempts=3,
    )

    result = controller.repair(
        request="Repair parser across multiple files",
        project_root="/tmp/project",
    )

    assert result.success is True
    assert result.stopped_safely is False
    assert len(result.attempts) == 2

    first = result.attempts[0]
    second = result.attempts[1]

    assert first.success is False
    assert first.rolled_back is True
    assert first.retryable is True
    assert "cross-file regression failed" in first.errors

    assert second.success is True
    assert "AUTONOMOUS RETRY CONTEXT:" in second.request
    assert "AUTONOMOUS REPAIR IMPROVEMENT:" in second.request

    reverification = MultiFileReverification().verify(
        {
            "success": True,
            "stage": "complete",
            "errors": [],
            "rolled_back": False,
        }
    )

    assert reverification.verified is True

    regression = MultiFileRegressionValidator().validate(
        {
            "success": True,
            "checked_files": [
                "parser.py",
                "utils.py",
            ],
            "failed_files": [],
        },
        expected_files=[
            "parser.py",
            "utils.py",
        ],
    )

    assert regression.verified is True

    recovery = MultiFileRecoveryManager().evaluate(
        {
            "success": False,
            "rolled_back": True,
        }
    )

    assert recovery.safe_to_continue is True
    assert recovery.rolled_back is True

    assert len(executor.calls) == 2


def test_full_autonomous_multifile_repair_stops_after_repeated_failure():
    class AlwaysFailExecutor:
        def __init__(self):
            self.calls = 0

        def execute(self, request, project_root):
            self.calls += 1
            return {
                "success": False,
                "stage": "post_apply_verification",
                "errors": ["verification failed"],
                "rolled_back": True,
            }

    executor = AlwaysFailExecutor()

    result = AutonomousMultiFileRepair(
        executor,
        max_attempts=2,
    ).repair(
        request="Repair project",
        project_root="/tmp/project",
    )

    assert result.success is False
    assert result.stopped_safely is True
    assert len(result.attempts) == 2
    assert executor.calls == 2
    assert "Maximum" in result.reason


def test_full_autonomous_multifile_repair_does_not_retry_unsafe_failure():
    class UnsafeExecutor:
        def execute(self, request, project_root):
            return {
                "success": False,
                "stage": "unknown",
                "errors": [],
                "rolled_back": False,
            }

    result = AutonomousMultiFileRepair(
        UnsafeExecutor(),
        max_attempts=3,
    ).repair(
        request="Repair project",
        project_root="/tmp/project",
    )

    assert result.success is False
    assert result.stopped_safely is True
    assert len(result.attempts) == 1
    assert "enough evidence" in result.reason.lower()
