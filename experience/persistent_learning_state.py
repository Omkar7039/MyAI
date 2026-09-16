from __future__ import annotations

import json

from core.runtime_state import RuntimeStateStore
from experience.learning_state import LearningAppliedChange


class PersistentLearningState:
    """
    Persist active governed learning state and its rollback history.

    Historical learning remains in ExperienceStore. This store contains
    the active governed configuration plus the in-process rollback stack
    needed to continue safe rollback after a restart.
    """

    KEY = "learning.governed.strategies"

    def __init__(
        self,
        store: RuntimeStateStore | None = None,
    ):
        self.store = store or RuntimeStateStore()

    @staticmethod
    def _serialize_change(
        change: LearningAppliedChange | None,
    ):
        if change is None:
            return None

        return {
            "strategy": change.strategy,
            "previous_score": change.previous_score,
            "applied_score": change.applied_score,
            "observations": change.observations,
            "confidence": change.confidence,
        }

    @staticmethod
    def _deserialize_change(item):
        if item is None:
            return None

        if not isinstance(item, dict):
            raise RuntimeError(
                "invalid governed learning state entry"
            )

        strategy = str(
            item.get("strategy", "")
        ).strip()

        if not strategy:
            raise RuntimeError(
                "persisted governed strategy must not be empty"
            )

        previous_score = item.get("previous_score")

        if previous_score is not None:
            previous_score = float(previous_score)

        try:
            return LearningAppliedChange(
                strategy=strategy,
                previous_score=previous_score,
                applied_score=float(item["applied_score"]),
                observations=int(item["observations"]),
                confidence=float(item["confidence"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(
                "invalid governed learning state values"
            ) from exc

    def save(
        self,
        changes: tuple[LearningAppliedChange, ...],
        history: dict[
            str,
            list[LearningAppliedChange | None],
        ] | None = None,
    ) -> None:
        payload = {
            "version": 2,
            "changes": [
                self._serialize_change(change)
                for change in changes
            ],
            "history": {
                strategy: [
                    self._serialize_change(item)
                    for item in items
                ]
                for strategy, items in sorted(
                    (history or {}).items()
                )
            },
        }

        self.store.set(
            self.KEY,
            json.dumps(
                payload,
                sort_keys=True,
            ),
        )

    def load(
        self,
    ) -> tuple[LearningAppliedChange, ...]:
        changes, _ = self.load_with_history()
        return changes

    def load_with_history(
        self,
    ) -> tuple[
        tuple[LearningAppliedChange, ...],
        dict[str, list[LearningAppliedChange | None]],
    ]:
        raw = self.store.value(self.KEY)

        if not raw:
            return (), {}

        try:
            payload = json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                "invalid persisted governed learning state"
            ) from exc

        # Backward compatibility with 6.26.3 format:
        # the persisted value was a plain list of changes.
        if isinstance(payload, list):
            changes = [
                self._deserialize_change(item)
                for item in payload
            ]

            return (
                tuple(
                    sorted(
                        changes,
                        key=lambda item: item.strategy,
                    )
                ),
                {},
            )

        if not isinstance(payload, dict):
            raise RuntimeError(
                "persisted governed learning state must be "
                "a list or object"
            )

        version = int(payload.get("version", 0))

        if version != 2:
            raise RuntimeError(
                f"unsupported governed learning state version: {version}"
            )

        raw_changes = payload.get("changes", [])

        if not isinstance(raw_changes, list):
            raise RuntimeError(
                "persisted governed learning changes must be a list"
            )

        changes = [
            self._deserialize_change(item)
            for item in raw_changes
        ]

        raw_history = payload.get("history", {})

        if not isinstance(raw_history, dict):
            raise RuntimeError(
                "persisted governed learning history must be an object"
            )

        history: dict[
            str,
            list[LearningAppliedChange | None],
        ] = {}

        for strategy, items in raw_history.items():
            name = str(strategy).strip()

            if not name:
                raise RuntimeError(
                    "persisted rollback strategy must not be empty"
                )

            if not isinstance(items, list):
                raise RuntimeError(
                    "persisted rollback history must be a list"
                )

            history[name] = [
                self._deserialize_change(item)
                for item in items
            ]

        return (
            tuple(
                sorted(
                    changes,
                    key=lambda item: item.strategy,
                )
            ),
            history,
        )

    def clear(self) -> None:
        self.store.delete(self.KEY)
