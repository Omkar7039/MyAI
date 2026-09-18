from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from core.runtime_recovery_controller import (
    RuntimeRecoveryController,
    RuntimeRecoveryExecution,
)
from core.task_supervisor import (
    TaskExecution,
    TaskSupervisor,
)


@dataclass(frozen=True)
class SupervisedTaskResult:
    task: TaskExecution
    recovery: RuntimeRecoveryExecution | None
    response: object | None


class SupervisedTaskRunner:
    """
    Execute a top-level task under task supervision and runtime recovery.

    The runner owns task-level retry/recovery decisions. Agent-level retry
    loops remain inside their existing agents.
    """

    def __init__(
        self,
        *,
        supervisor: TaskSupervisor | None = None,
        recovery_controller: RuntimeRecoveryController | None = None,
    ):
        self.supervisor = (
            supervisor or TaskSupervisor()
        )
        self.recovery_controller = (
            recovery_controller
            or RuntimeRecoveryController()
        )

    def run(
        self,
        *,
        task_id: str,
        execute: Callable[[], object],
        fingerprint: str,
        recover: Callable[[], bool] | None = None,
        max_task_retries: int | None = None,
    ) -> SupervisedTaskResult:
        if max_task_retries is not None:
            if max_task_retries < 0:
                raise ValueError(
                    "max_task_retries must be >= 0"
                )

        self.supervisor.create(task_id)
        self.supervisor.start(task_id)

        while True:
            try:
                response = execute()

            except Exception as exc:
                recovery = self.recovery_controller.handle(
                    fingerprint=fingerprint,
                    error=exc,
                    message=str(exc),
                    recover=recover,
                )

                if recovery.action == "continue":
                    task = self.supervisor.complete(
                        task_id,
                        reason=recovery.reason,
                    )

                    return SupervisedTaskResult(
                        task=task,
                        recovery=recovery,
                        response=None,
                    )

                if recovery.action == "retry":
                    current = self.supervisor.get(task_id)

                    if (
                        current is None
                        or max_task_retries is None
                        or current.attempt > max_task_retries
                    ):
                        task = self.supervisor.fail(
                            task_id,
                            recovery.reason,
                        )

                        return SupervisedTaskResult(
                            task=task,
                            recovery=recovery,
                            response=None,
                        )

                    retry = self.supervisor.retry(
                        task_id,
                        recovery.reason,
                    )

                    if retry.status == TaskSupervisor.FAILED:
                        return SupervisedTaskResult(
                            task=retry,
                            recovery=recovery,
                            response=None,
                        )

                    self.supervisor.start(task_id)
                    continue

                task = self.supervisor.fail(
                    task_id,
                    recovery.reason,
                )

                return SupervisedTaskResult(
                    task=task,
                    recovery=recovery,
                    response=None,
                )

            task = self.supervisor.complete(
                task_id,
            )

            return SupervisedTaskResult(
                task=task,
                recovery=None,
                response=response,
            )
