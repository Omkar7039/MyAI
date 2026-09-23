from core.runtime_services import RuntimeServices
from core.runtime_state import RuntimeStateStore
from core.task_resume import TaskResumeResult
from core.task_resume_report import TaskResumeReport


def test_runtime_services_resume_report(tmp_path):
    services = RuntimeServices.create(
        RuntimeStateStore(tmp_path / "runtime.db")
    )

    report = TaskResumeReport(
        recovered_at="2026-09-18T12:00:00+00:00",
        total_unfinished=2,
        requeued=1,
        reconciled=1,
        failed=0,
        actions=(
            TaskResumeResult(
                task_id="task-1",
                action="requeue",
                reason="unfinished task",
            ),
            TaskResumeResult(
                task_id="task-2",
                action="reconcile",
                reason="already completed",
            ),
        ),
    )

    services.task_resume_reports.save(report)

    assert services.resume_report() == report


def test_runtime_services_clear_resume_report(tmp_path):
    services = RuntimeServices.create(
        RuntimeStateStore(tmp_path / "runtime.db")
    )

    report = TaskResumeReport(
        recovered_at="2026-09-18T12:00:00+00:00",
        total_unfinished=1,
        requeued=1,
        reconciled=0,
        failed=0,
        actions=(
            TaskResumeResult(
                task_id="task-1",
                action="requeue",
                reason="unfinished task",
            ),
        ),
    )

    services.task_resume_reports.save(report)
    assert services.resume_report() is not None

    services.clear_resume_report()

    assert services.resume_report() is None


def test_clear_resume_report_is_idempotent(tmp_path):
    services = RuntimeServices.create(
        RuntimeStateStore(tmp_path / "runtime.db")
    )

    services.clear_resume_report()
    services.clear_resume_report()

    assert services.resume_report() is None
