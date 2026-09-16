from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from core.runtime_state import RuntimeStateStore
from experience.persistent_learning_state import PersistentLearningState


@dataclass(frozen=True)
class StateRecoveryResult:
    recovered: bool
    state_name: str
    quarantined_key: str | None
    reason: str


class RuntimeStateRecovery:
    """
    Safely recover malformed logical runtime state.

    Recovery never overwrites a valid state. The original malformed value
    is copied into a quarantine key before the affected key is removed.
    """

    QUARANTINE_PREFIX = "recovery.quarantine."

    def __init__(
        self,
        *,
        runtime_store: RuntimeStateStore | None = None,
    ):
        self.runtime_store = (
            runtime_store or RuntimeStateStore()
        )

    def recover_learning_state(
        self,
        *,
        state: PersistentLearningState,
        error: Exception,
    ) -> StateRecoveryResult:
        key = state.KEY
        raw = self.runtime_store.value(key)

        if raw is None:
            return StateRecoveryResult(
                recovered=False,
                state_name="learning",
                quarantined_key=None,
                reason="no persisted learning state was present",
            )

        quarantine_key = self._quarantine_key(
            "learning",
        )

        self.runtime_store.set(
            quarantine_key,
            raw,
        )

        state.clear()

        return StateRecoveryResult(
            recovered=True,
            state_name="learning",
            quarantined_key=quarantine_key,
            reason=(
                "malformed learning state was quarantined and "
                f"cleared: {error}"
            ),
        )

    def recover_runtime_value(
        self,
        *,
        key: str,
        error: Exception,
    ) -> StateRecoveryResult:
        name = key.strip()

        if not name:
            raise ValueError("key must not be empty")

        raw = self.runtime_store.value(name)

        if raw is None:
            return StateRecoveryResult(
                recovered=False,
                state_name=name,
                quarantined_key=None,
                reason="no persisted runtime value was present",
            )

        quarantine_key = self._quarantine_key(
            name,
        )

        self.runtime_store.set(
            quarantine_key,
            raw,
        )

        self.runtime_store.delete(name)

        return StateRecoveryResult(
            recovered=True,
            state_name=name,
            quarantined_key=quarantine_key,
            reason=(
                "malformed runtime value was quarantined and "
                f"cleared: {error}"
            ),
        )

    @staticmethod
    def _quarantine_key(
        name: str,
    ) -> str:
        stamp = datetime.now(
            timezone.utc
        ).strftime("%Y%m%d%H%M%S%f")

        return (
            f"{RuntimeStateRecovery.QUARANTINE_PREFIX}"
            f"{name}.{stamp}"
        )
