from __future__ import annotations

import re
from dataclasses import dataclass

from experience.learning_signal import (
    LearningSignal,
    LearningSignalType,
)
from experience.store import Experience, ExperienceStore


@dataclass(frozen=True)
class HistoricalLearningResult:
    signals: tuple[LearningSignal, ...]
    source_experience_ids: tuple[str, ...]
    retrieved: int


class HistoricalLearningRetriever:
    """
    Convert persisted learning experiences back into normalized
    LearningSignal objects.

    Only active experiences in category='learning' are considered.
    """

    _STRATEGY_RE = re.compile(
        r"(?:^|;\s*)strategy=([^;]*)",
        re.IGNORECASE,
    )

    _ATTEMPTS_RE = re.compile(
        r"(?:^|;\s*)attempts=(\d+)",
        re.IGNORECASE,
    )

    _SCORE_RE = re.compile(
        r"(?:^|;\s*)score=([0-9]+(?:\.[0-9]+)?)",
        re.IGNORECASE,
    )

    def __init__(self, store: ExperienceStore):
        self.store = store

    def recent(
        self,
        limit: int = 20,
    ) -> HistoricalLearningResult:
        experiences = self.store.recent(limit)

        return self._convert(experiences)

    def search(
        self,
        query: str,
        limit: int = 10,
    ) -> HistoricalLearningResult:
        experiences = self.store.search(
            query,
            limit,
        )

        return self._convert(experiences)

    def get(
        self,
        experience_id: str,
    ) -> LearningSignal | None:
        experience = self.store.get(experience_id)

        if experience is None:
            return None

        if not self._is_learning_experience(experience):
            return None

        return self._convert_one(experience)

    def _convert(
        self,
        experiences: list[Experience],
    ) -> HistoricalLearningResult:
        signals: list[LearningSignal] = []
        ids: list[str] = []

        for experience in experiences:
            if not self._is_learning_experience(experience):
                continue

            signal = self._convert_one(experience)

            if signal is None:
                continue

            signals.append(signal)
            ids.append(experience.experience_id)

        return HistoricalLearningResult(
            signals=tuple(signals),
            source_experience_ids=tuple(ids),
            retrieved=len(signals),
        )

    @classmethod
    def _convert_one(
        cls,
        experience: Experience,
    ) -> LearningSignal | None:
        try:
            signal_type = LearningSignalType(
                experience.action
            )
        except ValueError:
            return None

        strategy = cls._metadata_value(
            cls._STRATEGY_RE,
            experience.metadata,
            default="",
        )

        attempts_text = cls._metadata_value(
            cls._ATTEMPTS_RE,
            experience.metadata,
            default="1",
        )

        score_text = cls._metadata_value(
            cls._SCORE_RE,
            experience.metadata,
            default="0.0",
        )

        try:
            attempts = int(attempts_text)
            score = float(score_text)
        except ValueError:
            return None

        return LearningSignal(
            signal_type=signal_type,
            task=experience.task,
            strategy=strategy,
            attempts=attempts,
            score=score,
            metadata=experience.metadata,
        )

    @staticmethod
    def _metadata_value(
        pattern: re.Pattern[str],
        metadata: str,
        *,
        default: str,
    ) -> str:
        match = pattern.search(metadata or "")

        if match is None:
            return default

        return match.group(1).strip()

    @staticmethod
    def _is_learning_experience(
        experience: Experience,
    ) -> bool:
        return (
            experience.category == "learning"
            and experience.lifecycle_state == "active"
        )
