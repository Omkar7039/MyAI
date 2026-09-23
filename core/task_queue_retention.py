from __future__ import annotations

from dataclasses import dataclass

from core.task_queue import TaskQueue


@dataclass(frozen=True)
class TaskQueueRetentionResult:
    existing_terminal_tasks: int
    retained_terminal_tasks: int
    pruned_terminal_tasks: int
    active_tasks: int
    applied: bool


class TaskQueueRetentionManager:
    """
    Keep durable queue history bounded.

    Active work is never pruned:
      - queued
      - claimed

    Only terminal work is eligible:
      - completed
      - failed
    """

    TERMINAL_STATUSES = {"completed", "failed"}
    ACTIVE_STATUSES = {"queued", "claimed"}

    def __init__(
        self,
        queue: TaskQueue,
        *,
        max_terminal_tasks: int = 100,
    ):
        if max_terminal_tasks < 0:
            raise ValueError("max_terminal_tasks must be >= 0")

        self.queue = queue
        self.max_terminal_tasks = max_terminal_tasks

    def run(self, *, apply: bool = False) -> TaskQueueRetentionResult:
        tasks = self.queue.all()

        terminal = [
            task
            for task in tasks
            if task.status in self.TERMINAL_STATUSES
        ]

        active = [
            task
            for task in tasks
            if task.status in self.ACTIVE_STATUSES
        ]

        prune_count = max(
            0,
            len(terminal) - self.max_terminal_tasks,
        )

        to_prune = terminal[:prune_count]

        if apply:
            for task in to_prune:
                self.queue.remove(task.task_id)

        return TaskQueueRetentionResult(
            existing_terminal_tasks=len(terminal),
            retained_terminal_tasks=(
                len(terminal) - prune_count
            ),
            pruned_terminal_tasks=prune_count,
            active_tasks=len(active),
            applied=apply,
        )
