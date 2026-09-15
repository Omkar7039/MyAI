from agents.debug_investigation import DebugEvidence
from agents.debug_reinvestigator import DebugReinvestigator


class FakeInvestigator:
    def __init__(self, final):
        self.final = final
        self.calls = []

    def investigate(self, problem, code, error=None, language=None):
        self.calls.append(
            {
                "problem": problem,
                "code": code,
                "error": error,
                "language": language,
            }
        )
        return self.final


def make_original():
    return DebugEvidence(
        problem="Fix missing variable",
        language="python",
        error="NameError",
        static_analysis="undefined name detected",
        runtime={
            "language": "python",
            "success": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": "NameError: missing",
            "timed_out": False,
        },
    )


def make_success():
    return DebugEvidence(
        problem="Fix missing variable",
        language="python",
        error="NameError",
        static_analysis="clean",
        runtime={
            "language": "python",
            "success": True,
            "exit_code": 0,
            "stdout": "42",
            "stderr": "",
            "timed_out": False,
        },
    )


def make_failure():
    return DebugEvidence(
        problem="Fix missing variable",
        language="python",
        error="NameError",
        static_analysis="undefined name detected",
        runtime={
            "language": "python",
            "success": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": "NameError: missing",
            "timed_out": False,
        },
    )


def test_reinvestigation_marks_repair_resolved():
    investigator = FakeInvestigator(make_success())
    reinvestigator = DebugReinvestigator(investigator)

    result = reinvestigator.verify_repair(
        make_original(),
        "missing = 42\nprint(missing)",
    )

    assert result.resolved is True
    assert "no longer reproduced" in result.reason
    assert len(investigator.calls) == 1
    assert investigator.calls[0]["code"] == "missing = 42\nprint(missing)"


def test_reinvestigation_rejects_repair_when_failure_remains():
    investigator = FakeInvestigator(make_failure())
    reinvestigator = DebugReinvestigator(investigator)

    result = reinvestigator.verify_repair(
        make_original(),
        "print(missing)",
    )

    assert result.resolved is False
    assert "still reproduced" in result.reason


def test_reinvestigation_rejects_timeout():
    timeout = DebugEvidence(
        problem="Fix bug",
        language="python",
        error=None,
        static_analysis="analysis",
        runtime={
            "language": "python",
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": "timeout",
            "timed_out": True,
        },
    )

    investigator = FakeInvestigator(timeout)
    result = DebugReinvestigator(investigator).verify_repair(
        make_original(),
        "print(1)",
    )

    assert result.resolved is False
    assert "still reproduced" in result.reason


def test_reinvestigation_is_deterministic():
    original = make_original()
    repaired_code = "missing = 42\nprint(missing)"

    first = DebugReinvestigator(
        FakeInvestigator(make_success())
    ).verify_repair(
        original,
        repaired_code,
    )

    second = DebugReinvestigator(
        FakeInvestigator(make_success())
    ).verify_repair(
        original,
        repaired_code,
    )

    assert first == second
