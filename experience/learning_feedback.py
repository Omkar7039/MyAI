from __future__ import annotations

from dataclasses import dataclass

from experience.learning_signal import (
    LearningSignal,
    LearningSignalCollector,
)


@dataclass(frozen=True)
class LearningFeedback:
    signals: tuple[LearningSignal, ...]
    repair_success: bool
    verification_success: bool
    strategy: str
    score: float


class LearningFeedbackBuilder:
    """
    Convert concrete repair/verification outcomes into learning signals.

    This adapter does not persist anything and does not alter the
    underlying repair or verification result.
    """

    def __init__(
        self,
        collector: LearningSignalCollector | None = None,
    ):
        self.collector = collector or LearningSignalCollector()

    def build(
        self,
        *,
        task: str,
        strategy: str,
        repair_success: bool,
        verification_success: bool,
        attempts: int = 1,
        repair_score: float = 0.0,
        verification_score: float = 0.0,
        rolled_back: bool = False,
        retried: bool = False,
        metadata: str = "",
    ) -> LearningFeedback:
        if not strategy.strip():
            raise ValueError("strategy must not be empty")

        repair_score = max(
            0.0,
            min(100.0, float(repair_score)),
        )
        verification_score = max(
            0.0,
            min(100.0, float(verification_score)),
        )

        signals: list[LearningSignal] = []

        if repair_success:
            signals.append(
                self.collector.repair_success(
                    task,
                    strategy=strategy,
                    attempts=attempts,
                    score=repair_score,
                    metadata=metadata,
                )
            )
        else:
            signals.append(
                self.collector.repair_failure(
                    task,
                    strategy=strategy,
                    attempts=attempts,
                    score=repair_score,
                    metadata=metadata,
                )
            )

        if verification_success:
            signals.append(
                self.collector.verification_success(
                    task,
                    strategy=strategy,
                    attempts=attempts,
                    score=verification_score,
                    metadata=metadata,
                )
            )
        else:
            signals.append(
                self.collector.verification_failure(
                    task,
                    strategy=strategy,
                    attempts=attempts,
                    score=verification_score,
                    metadata=metadata,
                )
            )

        if retried:
            signals.append(
                self.collector.retry(
                    task,
                    strategy=strategy,
                    attempts=attempts,
                    score=verification_score,
                    metadata=metadata,
                )
            )

        if rolled_back:
            signals.append(
                self.collector.rollback(
                    task,
                    strategy=strategy,
                    attempts=attempts,
                    score=verification_score,
                    metadata=metadata,
                )
            )

        final_score = self._combined_score(
            repair_score=repair_score,
            verification_score=verification_score,
            repair_success=repair_success,
            verification_success=verification_success,
        )

        return LearningFeedback(
            signals=tuple(signals),
            repair_success=repair_success,
            verification_success=verification_success,
            strategy=strategy.strip(),
            score=final_score,
        )

    @staticmethod
    def _combined_score(
        *,
        repair_score: float,
        verification_score: float,
        repair_success: bool,
        verification_success: bool,
    ) -> float:
        repair_score = max(0.0, min(100.0, repair_score))
        verification_score = max(
            0.0,
            min(100.0, verification_score),
        )

        weighted = (
            repair_score * 0.5
            + verification_score * 0.5
        )

        if not repair_success:
            weighted *= 0.5

        if not verification_success:
            weighted *= 0.5

        return max(0.0, min(100.0, weighted))
