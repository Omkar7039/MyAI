from __future__ import annotations

import json

from core.runtime_state import RuntimeStateStore
from core.task_supervisor import (
    TaskExecution,
    TaskSupervisor,
)


class PersistentTaskSupervisor:
    """
    Persist top-level task lifecycle snapshots using RuntimeStateStore.

    The underlying TaskSupervisor remains the source of in-process state.
    Persistence is updated after every state-changing operation.
    """

    KEY = "runtime.tasks.executions"
    VERSION = 1

    def __init__(
        self,
        *,
        store: RuntimeStateStore,
        supervisor: TaskSupervisor | None = None,
    ):
        self.store = store
        self.supervisor = (
            supervisor or TaskSupervisor()
        )
        self._load()

    @staticmethod
    def _serialize(execution: TaskExecution) -> dict:
        return {
            "task_id": execution.task_id,
            "status": execution.status,
            "attempt": execution.attempt,
            "max_attempts": execution.max_attempts,
            "success": execution.success,
            "reason": execution.reason,
        }

    @staticmethod
    def _deserialize(item) -> TaskExecution:
        if not isinstance(item, dict):
            raise RuntimeError(
                "invalid persisted task execution"
            )

        try:
            task_id = str(
                item["task_id"]
            ).strip()

            if not task_id:
                raise ValueError(
                    "empty task id"
                )

            status = str(
                item["status"]
            ).strip()

            attempt = int(
                item["attempt"]
            )

            max_attempts = int(
                item["max_attempts"]
            )

            success = item["success"]

            if success is not None:
                success = bool(success)

            reason = str(
                item["reason"]
            ).strip()

            if not reason:
                raise ValueError(
                    "empty task reason"
                )

            return TaskExecution(
                task_id=task_id,
                status=status,
                attempt=attempt,
                max_attempts=max_attempts,
                success=success,
                reason=reason,
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise RuntimeError(
                "invalid persisted task execution values"
            ) from exc

    def _load(self) -> None:
        raw = self.store.value(self.KEY)

        if not raw:
            return

        try:
            payload = json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                "invalid persisted task supervision state"
            ) from exc

        if not isinstance(payload, dict):
            raise RuntimeError(
                "persisted task supervision state must be an object"
            )

        version = int(
            payload.get("version", 0)
        )

        if version != self.VERSION:
            raise RuntimeError(
                "unsupported persisted task supervision version: "
                f"{version}"
            )

        items = payload.get(
            "tasks",
            [],
        )

        if not isinstance(items, list):
            raise RuntimeError(
                "persisted task supervision tasks must be a list"
            )

        for item in items:
            execution = self._deserialize(item)
            self.supervisor._tasks[
                execution.task_id
            ] = execution

    def _save(self) -> None:
        tasks = [
            self._serialize(execution)
            for execution in self.supervisor.all_insertion_order()
        ]

        payload = {
            "version": self.VERSION,
            "tasks": tasks,
        }

        self.store.set(
            self.KEY,
            json.dumps(
                payload,
                sort_keys=True,
            ),
        )

    @property
    def max_attempts(self) -> int:
        return self.supervisor.max_attempts

    def create(self, task_id: str) -> TaskExecution:
        result = self.supervisor.create(task_id)
        self._save()
        return result

    def start(self, task_id: str) -> TaskExecution:
        result = self.supervisor.start(task_id)
        self._save()
        return result

    def retry(
        self,
        task_id: str,
        reason: str,
    ) -> TaskExecution:
        result = self.supervisor.retry(
            task_id,
            reason,
        )
        self._save()
        return result

    def complete(
        self,
        task_id: str,
        reason: str = "task completed successfully",
    ) -> TaskExecution:
        result = self.supervisor.complete(
            task_id,
            reason,
        )
        self._save()
        return result

    def fail(
        self,
        task_id: str,
        reason: str,
    ) -> TaskExecution:
        result = self.supervisor.fail(
            task_id,
            reason,
        )
        self._save()
        return result

    def stop(
        self,
        task_id: str,
        reason: str,
    ) -> TaskExecution:
        result = self.supervisor.stop(
            task_id,
            reason,
        )
        self._save()
        return result

    def get(
        self,
        task_id: str,
    ) -> TaskExecution | None:
        return self.supervisor.get(task_id)

    def all(self) -> tuple[TaskExecution, ...]:
        return self.supervisor.all()

    def all_insertion_order(self) -> tuple[TaskExecution, ...]:
        return self.supervisor.all_insertion_order()

    def remove(
        self,
        task_id: str,
    ) -> TaskExecution | None:
        result = self.supervisor.remove(task_id)
        if result is not None:
            self._save()
        return result

    def clear(self) -> None:
        self.supervisor.clear()
        self.store.delete(self.KEY)
