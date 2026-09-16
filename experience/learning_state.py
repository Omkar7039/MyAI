from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LearningAppliedChange:
    strategy: str
    previous_score: float | None
    applied_score: float
    observations: int
    confidence: float
