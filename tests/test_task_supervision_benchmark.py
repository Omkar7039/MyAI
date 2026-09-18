from __future__ import annotations

import time

from core.persistent_task_supervisor import (
    PersistentTaskSupervisor,
)
from core.runtime_state import RuntimeStateStore
from core.supervised_task_runner import (
    SupervisedTaskRunner,
)
from core.task_retention import TaskRetentionManager
from core.task_supervisor import TaskSupervisor


def _measure(operation, iterations: int) -> float:
    start = time.perf_counter()

    for _ in range(iterations):
        operation()

    return time.perf_counter() - start


def test_task_supervisor_lifecycle_benchmark():
    supervisor = TaskSupervisor(
        max_attempts=3,
    )

    iterations = 1000

    def lifecycle(index=[0]):
        index[0] += 1
        task_id = f"bench-{index[0]}"

        supervisor.create(task_id)
        supervisor.start(task_id)
        supervisor.complete(task_id)

    elapsed = _measure(
        lifecycle,
        iterations,
    )

    assert len(supervisor.all()) == iterations
    assert elapsed < 2.0

    print(
        f"\nTaskSupervisor lifecycle: "
        f"{elapsed:.4f}s/{iterations}"
    )


def test_persistent_task_supervisor_benchmark(tmp_path):
    store = RuntimeStateStore(
        tmp_path / "runtime.db"
    )

    supervisor = PersistentTaskSupervisor(
        store=store,
        supervisor=TaskSupervisor(
            max_attempts=3,
        ),
    )

    iterations = 100

    def create_completed(index=[0]):
        index[0] += 1
        task_id = f"persistent-{index[0]}"

        supervisor.create(task_id)
        supervisor.start(task_id)
        supervisor.complete(task_id)

    elapsed = _measure(
        create_completed,
        iterations,
    )

    assert len(supervisor.all()) == iterations
    assert elapsed < 2.0

    restarted = PersistentTaskSupervisor(
        store=RuntimeStateStore(
            tmp_path / "runtime.db"
        ),
        supervisor=TaskSupervisor(
            max_attempts=3,
        ),
    )

    assert len(restarted.all()) == iterations

    print(
        f"\nPersistentTaskSupervisor: "
        f"{elapsed:.4f}s/{iterations}"
    )


def test_task_retention_benchmark(tmp_path):
    store = RuntimeStateStore(
        tmp_path / "runtime.db"
    )

    supervisor = PersistentTaskSupervisor(
        store=store,
        supervisor=TaskSupervisor(
            max_attempts=3,
        ),
    )

    iterations = 100

    for index in range(iterations):
        task_id = f"retention-{index}"
        supervisor.create(task_id)
        supervisor.start(task_id)
        supervisor.complete(task_id)

    manager = TaskRetentionManager(
        supervisor,
        max_terminal_tasks=10,
    )

    elapsed = _measure(
        lambda: manager.run(apply=False),
        500,
    )

    result = manager.run(apply=False)

    assert result.existing_terminal_tasks == iterations
    assert result.retained_terminal_tasks == 10
    assert result.pruned_terminal_tasks == 90
    assert result.applied is False

    assert elapsed < 2.0

    print(
        f"\nTaskRetentionManager: "
        f"{elapsed:.4f}s/500"
    )


def test_supervised_task_runner_benchmark(tmp_path):
    runner = SupervisedTaskRunner(
        supervisor=TaskSupervisor(
            max_attempts=2,
        ),
    )

    iterations = 500

    def execute(index=[0]):
        index[0] += 1

        return f"result-{index[0]}"

    def run_task():
        current = execute()
        task_id = f"runner-{current}"

        return runner.run(
            task_id=task_id,
            execute=lambda current=current: current,
            fingerprint=f"runner:{task_id}",
        )

    elapsed = _measure(
        run_task,
        iterations,
    )

    result = runner.run(
        task_id="runner-final",
        execute=lambda: "final",
        fingerprint="runner:final",
    )

    assert result.response == "final"
    assert result.task.status == "completed"
    assert elapsed < 2.0

    print(
        f"\nSupervisedTaskRunner: "
        f"{elapsed:.4f}s/{iterations}"
    )


def test_persistent_task_history_load_benchmark(tmp_path):
    path = tmp_path / "runtime.db"

    first = PersistentTaskSupervisor(
        store=RuntimeStateStore(path),
        supervisor=TaskSupervisor(
            max_attempts=3,
        ),
    )

    for index in range(50):
        task_id = f"load-{index}"
        first.create(task_id)
        first.start(task_id)
        first.complete(task_id)

    iterations = 100

    elapsed = _measure(
        lambda: PersistentTaskSupervisor(
            store=RuntimeStateStore(path),
            supervisor=TaskSupervisor(
                max_attempts=3,
            ),
        ),
        iterations,
    )

    assert elapsed < 2.0

    final = PersistentTaskSupervisor(
        store=RuntimeStateStore(path),
        supervisor=TaskSupervisor(
            max_attempts=3,
        ),
    )

    assert len(final.all()) == 50

    print(
        f"\nPersistent task reload: "
        f"{elapsed:.4f}s/{iterations}"
    )
