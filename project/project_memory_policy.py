from __future__ import annotations

from dataclasses import dataclass

from project.project_memory_reconcile import ProjectMemoryReconciler


@dataclass(frozen=True)
class ProjectMemoryUpdateDecision:
    should_update: bool
    reason: str


class ProjectMemoryUpdatePolicy:
    def decide(self, reconciliation) -> ProjectMemoryUpdateDecision:
        if reconciliation.stored is None:
            return ProjectMemoryUpdateDecision(
                should_update=True,
                reason="No previous project snapshot exists.",
            )

        if reconciliation.changes.changed:
            return ProjectMemoryUpdateDecision(
                should_update=True,
                reason="Project state changed since the latest snapshot.",
            )

        return ProjectMemoryUpdateDecision(
            should_update=False,
            reason="Project state is unchanged.",
        )


class AutomaticProjectMemoryUpdater:
    def __init__(
        self,
        reconciler: ProjectMemoryReconciler | None = None,
        policy: ProjectMemoryUpdatePolicy | None = None,
    ):
        self.reconciler = reconciler or ProjectMemoryReconciler()
        self.policy = policy or ProjectMemoryUpdatePolicy()

    def update(self, context):
        reconciliation = self.reconciler.inspect(context)
        decision = self.policy.decide(reconciliation)

        if decision.should_update:
            self.reconciler.store.save(
                reconciliation.current
            )

        return reconciliation, decision
