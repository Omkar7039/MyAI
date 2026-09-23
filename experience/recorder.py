from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256

from experience.feedback import ExperienceFeedbackEngine
from experience.provenance import ExperienceProvenance
from experience.quality import ExperienceQualityChecker
from experience.store import Experience, ExperienceStore


@dataclass(frozen=True)
class RepairExperience:
    task: str
    action: str
    outcome: str
    success: bool
    lesson: str
    metadata: str = ""
    provenance: ExperienceProvenance | None = None


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
        self.quality_checker = ExperienceQualityChecker()
        self.feedback_engine = ExperienceFeedbackEngine()

    def record_repair(
        self,
        task: str,
        action: str,
        outcome: str,
        success: bool,
        lesson: str,
        metadata: str = "",
        provenance: ExperienceProvenance | None = None,
    ) -> Experience:
        experience = RepairExperience(
            task=task,
            action=action,
            outcome=outcome,
            success=success,
            lesson=lesson,
            metadata=metadata,
            provenance=provenance,
        )

        return self.record(experience)

    def record(
        self,
        experience: RepairExperience,
    ) -> Experience:
        quality = self.quality_checker.evaluate(
            task=experience.task,
            action=experience.action,
            outcome=experience.outcome,
            lesson=experience.lesson,
            success=experience.success,
        )

        feedback = self.feedback_engine.evaluate(
            task=experience.task,
            action=experience.action,
            outcome=experience.outcome,
            success=experience.success,
            lesson=experience.lesson,
            metadata=experience.metadata,
        )

        if not quality.accepted:
            raise ValueError(
                f"Experience rejected: {quality.reason}"
            )

        if not feedback.accepted:
            raise ValueError(
                "Experience rejected: insufficient actionable feedback."
            )

        experience_id = self._make_id(experience)

        stored = Experience(
            experience_id=experience_id,
            task=experience.task,
            category="repair",
            action=experience.action,
            outcome=experience.outcome,
            success=experience.success,
            lesson=feedback.improved_lesson,
            metadata=self._metadata_with_provenance(experience),
        )

        self.store.add(stored)

        return stored

    @staticmethod
    def _metadata_with_provenance(
        experience: RepairExperience,
    ) -> str:
        if experience.provenance is None:
            return experience.metadata

        payload = {
            "metadata": experience.metadata,
            "provenance": experience.provenance.to_metadata(),
        }

        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )

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
