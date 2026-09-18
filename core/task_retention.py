from __future__ import annotations

from dataclasses import dataclass

from core.persistent_task_supervisor import (
    PersistentTaskSupervisor,
)
from core.task_supervisor import TaskExecution


@dataclass(frozen=True)
class TaskRetentionResult:
    existing_terminal_tasks: int
    retained_terminal_tasks: int
    pruned_terminal_tasks: int
    active_tasks: int
    applied: bool


class TaskRetentionManager:
    """
    Bound persisted task history.

    Active tasks are always retained. Only terminal tasks are eligible for
    pruning, and the oldest terminal records are removed first according to
    task creation/insertion order.
    """

    TERMINAL_STATUSES = {
        "completed",
        "failed",
        "stopped",
    }

    def __init__(
        self,
        supervisor: PersistentTaskSupervisor,
        max_terminal_tasks: int = 100,
    ):
        if max_terminal_tasks < 0:
            raise ValueError(
                "max_terminal_tasks must be >= 0"
            )

        self.supervisor = supervisor
        self.max_terminal_tasks = max_terminal_tasks

    def run(
        self,
        *,
        apply: bool = False,
    ) -> TaskRetentionResult:
        tasks = self.supervisor.all_insertion_order()

        terminal = [
            task
            for task in tasks
            if task.status in self.TERMINAL_STATUSES
        ]

        active = [
            task
            for task in tasks
            if task.status not in self.TERMINAL_STATUSES
        ]

        existing_terminal = len(terminal)
        retained_terminal = min(
            existing_terminal,
            self.max_terminal_tasks,
        )
        prune_count = (
            existing_terminal - retained_terminal
        )

        if apply and prune_count:
            for task in terminal[:prune_count]:
                self.supervisor.remove(
                    task.task_id
                )

        return TaskRetentionResult(
            existing_terminal_tasks=existing_terminal,
            retained_terminal_tasks=retained_terminal,
            pruned_terminal_tasks=prune_count,
            active_tasks=len(active),
            applied=apply,
        )
