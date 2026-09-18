from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskExecution:
    task_id: str
    status: str
    attempt: int
    max_attempts: int
    success: bool | None
    reason: str


class TaskSupervisor:
    """
    Track the lifecycle of a top-level MyAI task.

    This layer supervises task state only. It does not execute agents,
    perform retries, mutate learning state, or call the model.
    """

    CREATED = "created"
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"

    def __init__(self, *, max_attempts: int = 3):
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")

        self.max_attempts = max_attempts
        self._tasks: dict[str, TaskExecution] = {}

    @staticmethod
    def _normalize_task_id(task_id: str) -> str:
        value = task_id.strip()

        if not value:
            raise ValueError("task_id must not be empty")

        return value

    @staticmethod
    def _normalize_reason(reason: str) -> str:
        value = reason.strip()

        if not value:
            raise ValueError("reason must not be empty")

        return value

    def create(self, task_id: str) -> TaskExecution:
        task_id = self._normalize_task_id(task_id)

        if task_id in self._tasks:
            raise ValueError(
                f"task already exists: {task_id}"
            )

        execution = TaskExecution(
            task_id=task_id,
            status=self.CREATED,
            attempt=0,
            max_attempts=self.max_attempts,
            success=None,
            reason="task created",
        )

        self._tasks[task_id] = execution
        return execution

    def start(self, task_id: str) -> TaskExecution:
        task_id = self._normalize_task_id(task_id)
        current = self._require(task_id)

        if current.status not in {
            self.CREATED,
            self.RETRYING,
        }:
            raise ValueError(
                f"task cannot start from status {current.status!r}"
            )

        attempt = current.attempt + 1

        if attempt > current.max_attempts:
            raise ValueError(
                "maximum task attempts reached"
            )

        execution = TaskExecution(
            task_id=task_id,
            status=self.RUNNING,
            attempt=attempt,
            max_attempts=current.max_attempts,
            success=None,
            reason="task execution started",
        )

        self._tasks[task_id] = execution
        return execution

    def retry(
        self,
        task_id: str,
        reason: str,
    ) -> TaskExecution:
        task_id = self._normalize_task_id(task_id)
        reason = self._normalize_reason(reason)

        current = self._require(task_id)

        if current.status != self.RUNNING:
            raise ValueError(
                f"task cannot retry from status {current.status!r}"
            )

        if current.attempt >= current.max_attempts:
            execution = TaskExecution(
                task_id=task_id,
                status=self.FAILED,
                attempt=current.attempt,
                max_attempts=current.max_attempts,
                success=False,
                reason="maximum task attempts reached",
            )

            self._tasks[task_id] = execution
            return execution

        execution = TaskExecution(
            task_id=task_id,
            status=self.RETRYING,
            attempt=current.attempt,
            max_attempts=current.max_attempts,
            success=None,
            reason=reason,
        )

        self._tasks[task_id] = execution
        return execution

    def complete(
        self,
        task_id: str,
        reason: str = "task completed successfully",
    ) -> TaskExecution:
        task_id = self._normalize_task_id(task_id)
        reason = self._normalize_reason(reason)

        current = self._require(task_id)

        if current.status != self.RUNNING:
            raise ValueError(
                f"task cannot complete from status {current.status!r}"
            )

        execution = TaskExecution(
            task_id=task_id,
            status=self.COMPLETED,
            attempt=current.attempt,
            max_attempts=current.max_attempts,
            success=True,
            reason=reason,
        )

        self._tasks[task_id] = execution
        return execution

    def fail(
        self,
        task_id: str,
        reason: str,
    ) -> TaskExecution:
        task_id = self._normalize_task_id(task_id)
        reason = self._normalize_reason(reason)

        current = self._require(task_id)

        if current.status != self.RUNNING:
            raise ValueError(
                f"task cannot fail from status {current.status!r}"
            )

        execution = TaskExecution(
            task_id=task_id,
            status=self.FAILED,
            attempt=current.attempt,
            max_attempts=current.max_attempts,
            success=False,
            reason=reason,
        )

        self._tasks[task_id] = execution
        return execution

    def stop(
        self,
        task_id: str,
        reason: str,
    ) -> TaskExecution:
        task_id = self._normalize_task_id(task_id)
        reason = self._normalize_reason(reason)

        current = self._require(task_id)

        if current.status not in {
            self.CREATED,
            self.RUNNING,
            self.RETRYING,
        }:
            raise ValueError(
                f"task cannot stop from status {current.status!r}"
            )

        execution = TaskExecution(
            task_id=task_id,
            status=self.STOPPED,
            attempt=current.attempt,
            max_attempts=current.max_attempts,
            success=False,
            reason=reason,
        )

        self._tasks[task_id] = execution
        return execution

    def get(self, task_id: str) -> TaskExecution | None:
        task_id = self._normalize_task_id(task_id)
        return self._tasks.get(task_id)

    def all(self) -> tuple[TaskExecution, ...]:
        return tuple(
            self._tasks[key]
            for key in sorted(self._tasks)
        )

    def all_insertion_order(self) -> tuple[TaskExecution, ...]:
        return tuple(self._tasks.values())

    def remove(self, task_id: str) -> TaskExecution | None:
        task_id = self._normalize_task_id(task_id)
        return self._tasks.pop(task_id, None)

    def clear(self) -> None:
        self._tasks.clear()

    def _require(self, task_id: str) -> TaskExecution:
        current = self._tasks.get(task_id)

        if current is None:
            raise KeyError(
                f"unknown task: {task_id}"
            )

        return current
