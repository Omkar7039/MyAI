from __future__ import annotations

from experience.learning_approval import (
    LearningApprovalDecision,
)
from experience.learning_change_proposal import (
    LearningChangeProposal,
)
from experience.learning_state import (
    LearningAppliedChange,
)
from experience.persistent_learning_state import (
    PersistentLearningState,
)



class LearningChangeApplication:
    """
    Apply only approved learning changes.

    This component owns a small in-memory learning state. It does not
    persist changes, perform routing, or approve proposals itself.
    """

    def __init__(
        self,
        *,
        persistent_state: PersistentLearningState | None = None,
    ):
        self._state: dict[str, LearningAppliedChange] = {}
        self._history: dict[
            str,
            list[LearningAppliedChange | None],
        ] = {}

        self.persistent_state = persistent_state

        if self.persistent_state is not None:
            changes, history = (
                self.persistent_state.load_with_history()
            )

            for change in changes:
                self._state[change.strategy] = change

            self._history = {
                strategy: list(items)
                for strategy, items in history.items()
            }

    def apply(
        self,
        *,
        proposal: LearningChangeProposal,
        approval: LearningApprovalDecision,
    ) -> LearningAppliedChange:
        if approval.strategy != proposal.strategy:
            raise ValueError(
                "approval and proposal strategies must match"
            )

        if not approval.approved:
            raise ValueError(
                "cannot apply an unapproved learning change"
            )

        strategy = proposal.strategy.strip()

        if not strategy:
            raise ValueError("strategy must not be empty")

        previous = self._state.get(strategy)

        self._history.setdefault(strategy, []).append(previous)

        change = LearningAppliedChange(
            strategy=strategy,
            previous_score=(
                previous.applied_score
                if previous is not None
                else None
            ),
            applied_score=proposal.proposed_score,
            observations=proposal.observations,
            confidence=approval.confidence,
        )

        self._state[strategy] = change

        if self.persistent_state is not None:
            self.persistent_state.save(
                self.all(),
                self._history,
            )

        return change

    def get(
        self,
        strategy: str,
    ) -> LearningAppliedChange | None:
        return self._state.get(strategy.strip())

    def all(
        self,
    ) -> tuple[LearningAppliedChange, ...]:
        return tuple(
            self._state[strategy]
            for strategy in sorted(self._state)
        )

    def rollback(
        self,
        strategy: str,
    ) -> LearningAppliedChange | None:
        name = strategy.strip()

        if not name:
            raise ValueError("strategy must not be empty")

        history = self._history.get(name)

        if not history:
            return None

        previous = history.pop()

        if not history:
            self._history.pop(name, None)

        if previous is None:
            self._state.pop(name, None)
        else:
            self._state[name] = previous

        if self.persistent_state is not None:
            self.persistent_state.save(
                self.all(),
                self._history,
            )

        return previous

    def can_rollback(
        self,
        strategy: str,
    ) -> bool:
        name = strategy.strip()

        if not name:
            raise ValueError("strategy must not be empty")

        return bool(self._history.get(name))

    def clear(self) -> None:
        self._state.clear()
        self._history.clear()

        if self.persistent_state is not None:
            self.persistent_state.clear()
