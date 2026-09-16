from __future__ import annotations

import json
import time

from core.runtime_state import RuntimeStateStore
from experience.learning_state import LearningAppliedChange
from experience.persistent_learning_state import PersistentLearningState


def _measure(operation, iterations: int) -> float:
    start = time.perf_counter()

    for _ in range(iterations):
        operation()

    return time.perf_counter() - start


def test_runtime_state_store_benchmark(tmp_path):
    store = RuntimeStateStore(tmp_path / "runtime_state.db")
    iterations = 1000

    write_time = _measure(
        lambda: store.set("benchmark.key", "value"),
        iterations,
    )

    read_time = _measure(
        lambda: store.get("benchmark.key"),
        iterations,
    )

    assert store.get("benchmark.key").value == "value"

    # Generous ceiling: this is a regression guard, not a microsecond benchmark.
    assert write_time < 2.0
    assert read_time < 2.0

    print(
        f"\nRuntimeStateStore: "
        f"writes={write_time:.4f}s/{iterations}, "
        f"reads={read_time:.4f}s/{iterations}"
    )


def test_persistent_learning_state_benchmark(tmp_path):
    runtime_store = RuntimeStateStore(tmp_path / "runtime_state.db")
    state = PersistentLearningState(runtime_store)

    change = LearningAppliedChange(
        strategy="property",
        previous_score=80.0,
        applied_score=90.0,
        observations=10,
        confidence=75.0,
    )

    changes = [change]
    history = {
        "property": [change, change, change],
        "standard": [change, change],
    }

    iterations = 250

    save_time = _measure(
        lambda: state.save(changes, history),
        iterations,
    )

    load_time = _measure(
        lambda: state.load_with_history(),
        iterations,
    )

    loaded_changes, loaded_history = state.load_with_history()

    assert len(loaded_changes) == 1
    assert loaded_changes[0].strategy == "property"
    assert "property" in loaded_history
    assert len(loaded_history["property"]) == 3

    assert save_time < 2.0
    assert load_time < 2.0

    print(
        f"\nPersistentLearningState: "
        f"saves={save_time:.4f}s/{iterations}, "
        f"loads={load_time:.4f}s/{iterations}"
    )


def test_runtime_benchmark_data_is_serializable(tmp_path):
    store = RuntimeStateStore(tmp_path / "runtime_state.db")
    store.set(
        "benchmark.metadata",
        json.dumps(
            {
                "phase": "6.26.8",
                "model_inference": False,
                "network": False,
            },
            sort_keys=True,
        ),
    )

    value = store.value("benchmark.metadata")
    metadata = json.loads(value)

    assert metadata["phase"] == "6.26.8"
    assert metadata["model_inference"] is False
    assert metadata["network"] is False
