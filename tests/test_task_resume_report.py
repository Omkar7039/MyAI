from core.runtime_state import RuntimeStateStore
from core.task_resume import TaskResumeResult
from core.task_resume_report import TaskResumeReport, TaskResumeReportStore


def make_report():
    return TaskResumeReport(
        recovered_at="2026-09-18T15:00:00",
        total_unfinished=3,
        requeued=2,
        reconciled=1,
        failed=0,
        actions=(
            TaskResumeResult(
                task_id="task-1",
                action="requeue",
                reason="unfinished running task moved to next attempt",
            ),
            TaskResumeResult(
                task_id="task-2",
                action="requeue",
                reason="queue entry had no supervisor record",
            ),
            TaskResumeResult(
                task_id="task-3",
                action="reconcile",
                reason="supervisor was already completed",
            ),
        ),
    )


def test_report_round_trip(tmp_path):
    store = RuntimeStateStore(tmp_path / "runtime.db")
    reports = TaskResumeReportStore(store)

    report = make_report()
    reports.save(report)

    restored = reports.load()

    assert restored == report


def test_report_persists_across_restart(tmp_path):
    path = tmp_path / "runtime.db"

    reports = TaskResumeReportStore(RuntimeStateStore(path))
    report = make_report()
    reports.save(report)

    restarted = TaskResumeReportStore(RuntimeStateStore(path))

    assert restarted.load() == report


def test_missing_report_returns_none(tmp_path):
    reports = TaskResumeReportStore(
        RuntimeStateStore(tmp_path / "runtime.db")
    )

    assert reports.load() is None


def test_malformed_report_returns_none(tmp_path):
    store = RuntimeStateStore(tmp_path / "runtime.db")
    reports = TaskResumeReportStore(store)

    store.set(reports.KEY, "{not valid json")

    assert reports.load() is None


def test_invalid_action_entries_are_ignored(tmp_path):
    store = RuntimeStateStore(tmp_path / "runtime.db")
    reports = TaskResumeReportStore(store)

    report = make_report()
    payload = report.to_dict()
    payload["actions"].append({"bad": "entry"})

    import json

    store.set(
        reports.KEY,
        json.dumps(
            {
                "version": 1,
                **payload,
            }
        ),
    )

    restored = reports.load()

    assert restored is not None
    assert restored.actions == report.actions


def test_clear_removes_report(tmp_path):
    store = RuntimeStateStore(tmp_path / "runtime.db")
    reports = TaskResumeReportStore(store)

    reports.save(make_report())
    reports.clear()

    assert reports.load() is None
