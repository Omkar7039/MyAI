from __future__ import annotations

from dataclasses import asdict, dataclass
import json

from core.runtime_state import RuntimeStateStore
from core.task_resume import TaskResumeResult


@dataclass(frozen=True)
class TaskResumeReport:
    recovered_at: str
    total_unfinished: int
    requeued: int
    reconciled: int
    failed: int
    actions: tuple[TaskResumeResult, ...]

    def to_dict(self) -> dict:
        return {
            "recovered_at": self.recovered_at,
            "total_unfinished": self.total_unfinished,
            "requeued": self.requeued,
            "reconciled": self.reconciled,
            "failed": self.failed,
            "actions": [asdict(action) for action in self.actions],
        }


class TaskResumeReportStore:
    KEY = "runtime.tasks.resume_report"
    VERSION = 1

    def __init__(self, store: RuntimeStateStore | None = None):
        self.store = store or RuntimeStateStore()

    def save(self, report: TaskResumeReport) -> None:
        payload = {
            "version": self.VERSION,
            **report.to_dict(),
        }
        self.store.set(self.KEY, json.dumps(payload))

    def load(self) -> TaskResumeReport | None:
        raw = self.store.value(self.KEY)

        if not raw:
            return None

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None

        if not isinstance(payload, dict):
            return None

        actions_raw = payload.get("actions", [])
        if not isinstance(actions_raw, list):
            return None

        actions: list[TaskResumeResult] = []

        for item in actions_raw:
            if not isinstance(item, dict):
                continue

            task_id = item.get("task_id")
            action = item.get("action")
            reason = item.get("reason")

            if not all(
                isinstance(value, str)
                for value in (task_id, action, reason)
            ):
                continue

            actions.append(
                TaskResumeResult(
                    task_id=task_id,
                    action=action,
                    reason=reason,
                )
            )

        try:
            return TaskResumeReport(
                recovered_at=str(payload["recovered_at"]),
                total_unfinished=int(payload["total_unfinished"]),
                requeued=int(payload["requeued"]),
                reconciled=int(payload["reconciled"]),
                failed=int(payload["failed"]),
                actions=tuple(actions),
            )
        except (KeyError, TypeError, ValueError):
            return None

    def clear(self) -> None:
        self.store.delete(self.KEY)
