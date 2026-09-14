from __future__ import annotations

from dataclasses import dataclass

from experience.lifecycle import ExperienceLifecycleDecision, ExperienceLifecycleManager
from experience.store import ExperienceStore


@dataclass(frozen=True)
class LifecycleMaintenanceReport:
    scanned: int
    retained: int
    archived: int
    deleted: int
    decisions: tuple[ExperienceLifecycleDecision, ...]


class ExperienceLifecycleMaintenance:
    """Apply lifecycle policy to stored experiences safely."""

    def __init__(
        self,
        store: ExperienceStore | None = None,
        manager: ExperienceLifecycleManager | None = None,
    ):
        self.store = store or ExperienceStore()
        self.manager = manager or ExperienceLifecycleManager()

    def run(
        self,
        limit: int = 1000,
        apply: bool = False,
        now=None,
    ) -> LifecycleMaintenanceReport:
        if limit < 1:
            raise ValueError("limit must be >= 1")

        experiences = self.store.recent(limit=limit)
        decisions = []
        retained = 0
        archived = 0
        deleted = 0

        for experience in experiences:
            decision = self.manager.classify(
                experience,
                now=now,
            )
            decisions.append(decision)

            if decision.action == "retain":
                retained += 1
                continue

            if not apply:
                if decision.action == "archive":
                    archived += 1
                elif decision.action == "delete":
                    deleted += 1
                continue

            if decision.action == "archive":
                if self.store.archive(experience.experience_id):
                    archived += 1
            elif decision.action == "delete":
                if self.store.delete(experience.experience_id):
                    deleted += 1

        return LifecycleMaintenanceReport(
            scanned=len(experiences),
            retained=retained,
            archived=archived,
            deleted=deleted,
            decisions=tuple(decisions),
        )
