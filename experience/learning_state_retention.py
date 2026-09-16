from __future__ import annotations

from dataclasses import dataclass

from experience.learning_state import LearningAppliedChange
from experience.persistent_learning_state import PersistentLearningState


@dataclass(frozen=True)
class LearningStateRetentionResult:
    strategy: str
    existing_entries: int
    retained_entries: int
    pruned_entries: int


@dataclass(frozen=True)
class LearningStateRetentionReport:
    scanned_strategies: int
    retained_entries: int
    pruned_entries: int
    applied: bool
    results: tuple[LearningStateRetentionResult, ...]


class LearningStateRetentionManager:
    """
    Bound persisted governed-learning rollback history.

    Active governed strategy state is always retained. Only older rollback
    entries beyond the configured depth are eligible for cleanup.
    """

    def __init__(
        self,
        state: PersistentLearningState,
        max_rollback_entries: int = 10,
    ):
        if max_rollback_entries < 0:
            raise ValueError(
                "max_rollback_entries must be >= 0"
            )

        self.state = state
        self.max_rollback_entries = max_rollback_entries

    def run(
        self,
        *,
        apply: bool = False,
    ) -> LearningStateRetentionReport:
        changes, history = self.state.load_with_history()

        results = []
        retained_entries = 0
        pruned_entries = 0

        for strategy in sorted(history):
            entries = history[strategy]
            existing = len(entries)

            if existing <= self.max_rollback_entries:
                kept = existing
                pruned = 0
                retained_entries += kept
            else:
                kept = self.max_rollback_entries
                pruned = existing - kept
                retained_entries += kept
                pruned_entries += pruned

                if apply:
                    history[strategy] = (
                        entries[-self.max_rollback_entries:]
                        if self.max_rollback_entries > 0
                        else []
                    )

            results.append(
                LearningStateRetentionResult(
                    strategy=strategy,
                    existing_entries=existing,
                    retained_entries=kept,
                    pruned_entries=pruned,
                )
            )

        if apply and pruned_entries:
            self.state.save(
                changes=changes,
                history=history,
            )

        return LearningStateRetentionReport(
            scanned_strategies=len(history),
            retained_entries=retained_entries,
            pruned_entries=pruned_entries,
            applied=apply,
            results=tuple(results),
        )
