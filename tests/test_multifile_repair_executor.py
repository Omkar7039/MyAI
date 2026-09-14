from pathlib import Path

from agents.multi_file_repair_executor import MultiFileRepairExecutor


class FakePlanner:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def build_patch_set(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class FakeApplier:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def apply(self, patch_set):
        self.calls.append(patch_set)
        return self.result


class FakeRecorder:
    def __init__(self):
        self.calls = []

    def record(self, **kwargs):
        self.calls.append(kwargs)


class Plan:
    targets = []
    affected_files = []


def _executor(planner, applier, recorder):
    executor = MultiFileRepairExecutor.__new__(
        MultiFileRepairExecutor
    )

    executor.root = Path("/Users/omkar/MyAI")
    executor.planner = planner
    executor.applier = applier
    executor.outcome_recorder = recorder

    return executor


def test_executor_applies_patch_and_records_real_success():
    planner = FakePlanner(
        {
            "success": True,
            "patch_set": "PATCHSET",
            "errors": [],
            "warnings": [],
        }
    )

    applier = FakeApplier(
        {
            "success": True,
            "stage": "complete",
            "errors": [],
            "warnings": [],
            "applied_files": [
                "agents/repair.py",
                "project/project_agent.py",
            ],
            "rolled_back": False,
        }
    )

    recorder = FakeRecorder()

    executor = _executor(
        planner,
        applier,
        recorder,
    )

    result = executor.execute(
        request="Fix parser validation across multiple files",
        plan=Plan(),
        evidence="Current source evidence",
        model_response='{"patches":[]}',
    )

    assert result["success"] is True
    assert result["stage"] == "complete"
    assert applier.calls == ["PATCHSET"]

    assert len(recorder.calls) == 1
    assert recorder.calls[0]["result"]["success"] is True
    assert recorder.calls[0]["result"]["stage"] == "complete"


def test_executor_stops_when_patch_planning_fails():
    planner = FakePlanner(
        {
            "success": False,
            "patch_set": None,
            "errors": [
                "No authorized patches were returned."
            ],
            "warnings": [],
        }
    )

    applier = FakeApplier(
        {
            "success": True,
            "stage": "complete",
            "errors": [],
            "warnings": [],
            "applied_files": [],
            "rolled_back": False,
        }
    )

    recorder = FakeRecorder()

    executor = _executor(
        planner,
        applier,
        recorder,
    )

    result = executor.execute(
        request="Fix parser validation across multiple files",
        plan=Plan(),
        evidence="Current source evidence",
    )

    assert result["success"] is False
    assert result["stage"] == "patch_planning"
    assert applier.calls == []

    assert len(recorder.calls) == 1
    assert recorder.calls[0]["result"]["success"] is False
    assert recorder.calls[0]["result"]["stage"] == "patch_planning"


def test_executor_can_disable_experience_recording():
    planner = FakePlanner(
        {
            "success": False,
            "patch_set": None,
            "errors": ["Planning failed."],
            "warnings": [],
        }
    )

    applier = FakeApplier({})
    recorder = FakeRecorder()

    executor = _executor(
        planner,
        applier,
        recorder,
    )

    result = executor.execute(
        request="Test",
        plan=Plan(),
        evidence="Evidence",
        record_experience=False,
    )

    assert result["success"] is False
    assert recorder.calls == []
