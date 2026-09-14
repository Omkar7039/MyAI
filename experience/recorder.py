from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from experience.store import Experience, ExperienceStore


@dataclass(frozen=True)
class RepairExperience:
    task: str
    action: str
    outcome: str
    success: bool
    lesson: str
    metadata: str = ""


class ExperienceRecorder:
    """
    Records verified outcomes from MyAI workflows.

    This component only records what the caller reports.
    It does not decide whether a repair is correct.
    """

    def __init__(
        self,
        store: ExperienceStore | None = None,
    ):
        self.store = store or ExperienceStore(
            "data/experience.db"
        )

    def record_repair(
        self,
        task: str,
        action: str,
        outcome: str,
        success: bool,
        lesson: str,
        metadata: str = "",
    ) -> Experience:
        experience = RepairExperience(
            task=task,
            action=action,
            outcome=outcome,
            success=success,
            lesson=lesson,
            metadata=metadata,
        )

        return self.record(experience)

    def record(
        self,
        experience: RepairExperience,
    ) -> Experience:
        experience_id = self._make_id(experience)

        stored = Experience(
            experience_id=experience_id,
            task=experience.task,
            category="repair",
            action=experience.action,
            outcome=experience.outcome,
            success=experience.success,
            lesson=experience.lesson,
            metadata=experience.metadata,
        )

        self.store.add(stored)

        return stored

    @staticmethod
    def _make_id(
        experience: RepairExperience,
    ) -> str:
        identity = "|".join(
            [
                experience.task,
                experience.action,
                experience.outcome,
                str(experience.success),
                experience.lesson,
                experience.metadata,
            ]
        )

        digest = sha256(
            identity.encode("utf-8")
        ).hexdigest()[:24]

        return f"repair-{digest}"
