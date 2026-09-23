from __future__ import annotations

from dataclasses import dataclass

from core.persistent_task_supervisor import PersistentTaskSupervisor
from core.task_queue import QueuedTask, TaskQueue


@dataclass(frozen=True)
class ClaimedTask:
    queued: QueuedTask
    supervisor_task_id: str


class TaskQueueCoordinator:
    """
    Coordinates durable queued work with persistent task supervision.

    Queue state answers: "What work is waiting?"
    Supervisor state answers: "What happened while executing it?"
    """

    def __init__(
        self,
        queue: TaskQueue | None = None,
        supervisor: PersistentTaskSupervisor | None = None,
    ):
        self.queue = queue or TaskQueue()
        self.supervisor = supervisor or PersistentTaskSupervisor(
            store=self.queue.store
        )

    def submit(
        self,
        task_id: str,
        payload: str,
        *,
        priority: int = 0,
    ) -> QueuedTask:
        if self.supervisor.get(task_id) is not None:
            raise ValueError(f"task already exists in supervisor: {task_id}")

        return self.queue.enqueue(
            task_id,
            payload,
            priority=priority,
        )

    def claim_next(self) -> ClaimedTask | None:
        queued = self.queue.claim_next()

        if queued is None:
            return None

        existing = self.supervisor.get(queued.task_id)

        try:
            if existing is None:
                self.supervisor.create(queued.task_id)
                self.supervisor.start(queued.task_id)
            elif existing.status == "retrying":
                self.supervisor.start(queued.task_id)
            elif existing.status == "running":
                raise RuntimeError(
                    f"task is already running: {queued.task_id}"
                )
            else:
                raise RuntimeError(
                    "cannot claim task with terminal supervisor state: "
                    f"{queued.task_id} ({existing.status})"
                )
        except Exception:
            self.queue.fail(queued.task_id)
            raise

        return ClaimedTask(
            queued=queued,
            supervisor_task_id=queued.task_id,
        )

    def complete(self, task_id: str, reason: str = "completed") -> None:
        self.supervisor.complete(task_id, reason=reason)
        self.queue.complete(task_id)

    def fail(self, task_id: str, reason: str = "failed") -> None:
        self.supervisor.fail(task_id, reason=reason)
        self.queue.fail(task_id)

    def get_queued(self, task_id: str) -> QueuedTask | None:
        return self.queue.get(task_id)

    def get_supervised(self, task_id: str):
        return self.supervisor.get(task_id)

    def queued(self) -> tuple[QueuedTask, ...]:
        return self.queue.queued()

    def active(self):
        return self.supervisor.all()

    def all_queued(self) -> tuple[QueuedTask, ...]:
        return self.queue.all()
