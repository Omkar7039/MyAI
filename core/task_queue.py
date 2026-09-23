from __future__ import annotations

from dataclasses import dataclass
import json

from core.runtime_state import RuntimeStateStore


@dataclass(frozen=True)
class QueuedTask:
    task_id: str
    payload: str
    priority: int = 0
    status: str = "queued"


class TaskQueue:
    KEY = "runtime.tasks.queue"
    VERSION = 1

    VALID_STATUSES = {"queued", "claimed", "completed", "failed"}

    def __init__(self, store: RuntimeStateStore | None = None):
        self.store = store or RuntimeStateStore()
        self._tasks: list[QueuedTask] = []
        self._load()

    def _serialize(self) -> dict:
        return {
            "version": self.VERSION,
            "tasks": [
                {
                    "task_id": task.task_id,
                    "payload": task.payload,
                    "priority": task.priority,
                    "status": task.status,
                }
                for task in self._tasks
            ],
        }

    def _deserialize(self, value: object) -> list[QueuedTask]:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return []

        if not isinstance(value, dict):
            return []

        tasks = value.get("tasks", [])
        if not isinstance(tasks, list):
            return []

        result: list[QueuedTask] = []

        for item in tasks:
            if not isinstance(item, dict):
                continue

            task_id = item.get("task_id")
            payload = item.get("payload")
            priority = item.get("priority", 0)
            status = item.get("status", "queued")

            if not isinstance(task_id, str) or not task_id:
                continue
            if not isinstance(payload, str):
                continue
            if not isinstance(priority, int):
                continue
            if status not in self.VALID_STATUSES:
                continue

            result.append(
                QueuedTask(
                    task_id=task_id,
                    payload=payload,
                    priority=priority,
                    status=status,
                )
            )

        return result

    def _load(self) -> None:
        self._tasks = self._deserialize(self.store.value(self.KEY))

    def _save(self) -> None:
        self.store.set(self.KEY, json.dumps(self._serialize()))

    def enqueue(
        self,
        task_id: str,
        payload: str,
        *,
        priority: int = 0,
    ) -> QueuedTask:
        if not task_id:
            raise ValueError("task_id must not be empty")
        if not isinstance(payload, str):
            raise TypeError("payload must be a string")
        if not isinstance(priority, int):
            raise TypeError("priority must be an integer")
        if any(task.task_id == task_id for task in self._tasks):
            raise ValueError(f"task already exists: {task_id}")

        task = QueuedTask(
            task_id=task_id,
            payload=payload,
            priority=priority,
            status="queued",
        )
        self._tasks.append(task)
        self._save()
        return task

    def claim_next(self) -> QueuedTask | None:
        queued = [
            task
            for task in self._tasks
            if task.status == "queued"
        ]

        if not queued:
            return None

        selected = max(
            enumerate(queued),
            key=lambda item: (item[1].priority, -item[0]),
        )[1]

        claimed = QueuedTask(
            task_id=selected.task_id,
            payload=selected.payload,
            priority=selected.priority,
            status="claimed",
        )

        self._tasks = [
            claimed if task.task_id == selected.task_id else task
            for task in self._tasks
        ]
        self._save()
        return claimed

    def requeue(self, task_id: str) -> QueuedTask:
        task = self.get(task_id)

        if task is None:
            raise KeyError(task_id)

        if task.status != "claimed":
            raise ValueError(
                f"task must be claimed before requeue: {task_id}"
            )

        return self._set_status(task_id, "queued")

    def complete(self, task_id: str) -> QueuedTask:
        return self._set_status(task_id, "completed")

    def fail(self, task_id: str) -> QueuedTask:
        return self._set_status(task_id, "failed")

    def _set_status(self, task_id: str, status: str) -> QueuedTask:
        if status not in self.VALID_STATUSES:
            raise ValueError(f"invalid status: {status}")

        found = None
        updated: list[QueuedTask] = []

        for task in self._tasks:
            if task.task_id == task_id:
                found = QueuedTask(
                    task_id=task.task_id,
                    payload=task.payload,
                    priority=task.priority,
                    status=status,
                )
                updated.append(found)
            else:
                updated.append(task)

        if found is None:
            raise KeyError(task_id)

        self._tasks = updated
        self._save()
        return found

    def get(self, task_id: str) -> QueuedTask | None:
        return next(
            (task for task in self._tasks if task.task_id == task_id),
            None,
        )

    def all(self) -> tuple[QueuedTask, ...]:
        return tuple(self._tasks)

    def queued(self) -> tuple[QueuedTask, ...]:
        return tuple(task for task in self._tasks if task.status == "queued")

    def active(self) -> tuple[QueuedTask, ...]:
        return tuple(task for task in self._tasks if task.status == "claimed")

    def remove(self, task_id: str) -> None:
        before = len(self._tasks)
        self._tasks = [
            task for task in self._tasks if task.task_id != task_id
        ]

        if len(self._tasks) == before:
            raise KeyError(task_id)

        self._save()

    def clear(self) -> None:
        self._tasks.clear()
        self._save()
