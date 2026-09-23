from __future__ import annotations

from dataclasses import dataclass

from core.task_queue_coordinator import TaskQueueCoordinator


@dataclass(frozen=True)
class TaskResumeResult:
    task_id: str
    action: str
    reason: str


class TaskResumeManager:
    """
    Reconciles durable queued work after a process restart.

    Claimed queue entries represent work that may have been interrupted.
    Running supervisor entries are advanced to a new supervised attempt.
    """

    def __init__(self, coordinator: TaskQueueCoordinator):
        self.coordinator = coordinator

    def recover_unfinished(self) -> tuple[TaskResumeResult, ...]:
        results: list[TaskResumeResult] = []

        for queued in self.coordinator.queue.active():
            supervised = self.coordinator.supervisor.get(queued.task_id)

            if supervised is None:
                self.coordinator.queue.requeue(queued.task_id)
                results.append(
                    TaskResumeResult(
                        task_id=queued.task_id,
                        action="requeue",
                        reason="queue entry had no supervisor record",
                    )
                )
                continue

            if supervised.status == "running":
                recovered = self.coordinator.supervisor.retry(
                    queued.task_id,
                    reason="resuming unfinished task after restart",
                )

                if recovered.status == "failed":
                    self.coordinator.queue.fail(queued.task_id)
                    results.append(
                        TaskResumeResult(
                            task_id=queued.task_id,
                            action="failed",
                            reason="supervisor retry limit reached",
                        )
                    )
                else:
                    self.coordinator.queue.requeue(queued.task_id)
                    results.append(
                        TaskResumeResult(
                            task_id=queued.task_id,
                            action="requeue",
                            reason="unfinished running task moved to next attempt",
                        )
                    )
                continue

            if supervised.status == "retrying":
                self.coordinator.queue.requeue(queued.task_id)
                results.append(
                    TaskResumeResult(
                        task_id=queued.task_id,
                        action="requeue",
                        reason="unfinished retrying task made runnable",
                    )
                )
                continue

            if supervised.status == "completed":
                self.coordinator.queue.complete(queued.task_id)
                results.append(
                    TaskResumeResult(
                        task_id=queued.task_id,
                        action="reconcile",
                        reason="supervisor was already completed",
                    )
                )
                continue

            if supervised.status in {"failed", "stopped"}:
                self.coordinator.queue.fail(queued.task_id)
                results.append(
                    TaskResumeResult(
                        task_id=queued.task_id,
                        action="reconcile",
                        reason=f"supervisor was already {supervised.status}",
                    )
                )
                continue

            raise RuntimeError(
                f"unknown supervisor state for {queued.task_id}: "
                f"{supervised.status}"
            )

        return tuple(results)
