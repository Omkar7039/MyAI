from agents.autonomous_multifile_repair import (
    AutonomousMultiFileRepair,
)


class FakeExecutor:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = []

    def execute(self, request, project_root):
        self.calls.append(
            {
                "request": request,
                "project_root": project_root,
            }
        )
        return next(self.results)


def test_autonomous_multifile_repair_succeeds_on_first_attempt():
    executor = FakeExecutor(
        [
            {
                "success": True,
                "stage": "complete",
                "errors": [],
                "rolled_back": False,
            }
        ]
    )

    result = AutonomousMultiFileRepair(
        executor,
        max_attempts=3,
    ).repair(
        request="repair project",
        project_root="/tmp/project",
    )

    assert result.success is True
    assert len(result.attempts) == 1
    assert result.attempts[0].success is True
    assert result.stopped_safely is False
    assert len(executor.calls) == 1


def test_autonomous_multifile_repair_retries_after_failure():
    executor = FakeExecutor(
        [
            {
                "success": False,
                "stage": "post_apply_verification",
                "errors": ["verification failed"],
                "rolled_back": True,
            },
            {
                "success": True,
                "stage": "complete",
                "errors": [],
                "rolled_back": False,
            },
        ]
    )

    result = AutonomousMultiFileRepair(
        executor,
        max_attempts=3,
    ).repair(
        request="repair project",
        project_root="/tmp/project",
    )

    assert result.success is True
    assert len(result.attempts) == 2
    assert result.attempts[0].success is False
    assert result.attempts[0].rolled_back is True
    assert result.attempts[1].success is True
    assert len(executor.calls) == 2


def test_autonomous_multifile_repair_stops_at_attempt_limit():
    executor = FakeExecutor(
        [
            {
                "success": False,
                "stage": "post_apply_verification",
                "errors": ["verification failed"],
                "rolled_back": True,
            },
            {
                "success": False,
                "stage": "post_apply_verification",
                "errors": ["verification failed again"],
                "rolled_back": True,
            },
            {
                "success": False,
                "stage": "post_apply_verification",
                "errors": ["still failing"],
                "rolled_back": True,
            },
        ]
    )

    result = AutonomousMultiFileRepair(
        executor,
        max_attempts=3,
    ).repair(
        request="repair project",
        project_root="/tmp/project",
    )

    assert result.success is False
    assert len(result.attempts) == 3
    assert result.stopped_safely is True
    assert "Maximum" in result.reason
    assert len(executor.calls) == 3


def test_autonomous_multifile_repair_rejects_invalid_attempt_limit():
    try:
        AutonomousMultiFileRepair(
            FakeExecutor([]),
            max_attempts=0,
        )
    except ValueError as exc:
        assert str(exc) == "max_attempts must be >= 1"
    else:
        raise AssertionError("Expected ValueError")
