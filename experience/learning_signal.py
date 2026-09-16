from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LearningSignalType(str, Enum):
    REPAIR_SUCCESS = "repair_success"
    REPAIR_FAILURE = "repair_failure"
    VERIFICATION_SUCCESS = "verification_success"
    VERIFICATION_FAILURE = "verification_failure"
    RETRY = "retry"
    ROLLBACK = "rollback"


@dataclass(frozen=True)
class LearningSignal:
    signal_type: LearningSignalType
    task: str
    strategy: str = ""
    attempts: int = 1
    score: float = 0.0
    metadata: str = ""


class LearningSignalCollector:
    """
    Collect deterministic learning signals from repair and verification
    outcomes. This layer only normalizes observations; it does not
    persist or modify existing experience records.
    """

    def repair_success(
        self,
        task: str,
        *,
        strategy: str = "",
        attempts: int = 1,
        score: float = 100.0,
        metadata: str = "",
    ) -> LearningSignal:
        return self._build(
            LearningSignalType.REPAIR_SUCCESS,
            task,
            strategy=strategy,
            attempts=attempts,
            score=score,
            metadata=metadata,
        )

    def repair_failure(
        self,
        task: str,
        *,
        strategy: str = "",
        attempts: int = 1,
        score: float = 0.0,
        metadata: str = "",
    ) -> LearningSignal:
        return self._build(
            LearningSignalType.REPAIR_FAILURE,
            task,
            strategy=strategy,
            attempts=attempts,
            score=score,
            metadata=metadata,
        )

    def verification_success(
        self,
        task: str,
        *,
        strategy: str = "",
        attempts: int = 1,
        score: float = 100.0,
        metadata: str = "",
    ) -> LearningSignal:
        return self._build(
            LearningSignalType.VERIFICATION_SUCCESS,
            task,
            strategy=strategy,
            attempts=attempts,
            score=score,
            metadata=metadata,
        )

    def verification_failure(
        self,
        task: str,
        *,
        strategy: str = "",
        attempts: int = 1,
        score: float = 0.0,
        metadata: str = "",
    ) -> LearningSignal:
        return self._build(
            LearningSignalType.VERIFICATION_FAILURE,
            task,
            strategy=strategy,
            attempts=attempts,
            score=score,
            metadata=metadata,
        )

    def retry(
        self,
        task: str,
        *,
        strategy: str = "",
        attempts: int = 1,
        score: float = 0.0,
        metadata: str = "",
    ) -> LearningSignal:
        return self._build(
            LearningSignalType.RETRY,
            task,
            strategy=strategy,
            attempts=attempts,
            score=score,
            metadata=metadata,
        )

    def rollback(
        self,
        task: str,
        *,
        strategy: str = "",
        attempts: int = 1,
        score: float = 0.0,
        metadata: str = "",
    ) -> LearningSignal:
        return self._build(
            LearningSignalType.ROLLBACK,
            task,
            strategy=strategy,
            attempts=attempts,
            score=score,
            metadata=metadata,
        )

    @staticmethod
    def _build(
        signal_type: LearningSignalType,
        task: str,
        *,
        strategy: str,
        attempts: int,
        score: float,
        metadata: str,
    ) -> LearningSignal:
        if not task.strip():
            raise ValueError("task must not be empty")

        if attempts < 1:
            raise ValueError("attempts must be at least 1")

        if not 0.0 <= score <= 100.0:
            raise ValueError("score must be between 0 and 100")

        return LearningSignal(
            signal_type=signal_type,
            task=task.strip(),
            strategy=strategy.strip(),
            attempts=attempts,
            score=float(score),
            metadata=metadata.strip(),
        )
