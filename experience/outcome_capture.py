from __future__ import annotations

from dataclasses import dataclass

from experience.learning_feedback import (
    LearningFeedback,
    LearningFeedbackBuilder,
)


@dataclass(frozen=True)
class CapturedOutcome:
    task: str
    strategy: str
    feedback: LearningFeedback
    captured: bool


class AutomaticOutcomeCapture:
    """
    Capture a concrete repair/verification outcome and normalize it
    through the existing LearningFeedbackBuilder.

    This component is intentionally side-effect free:
    - no persistence
    - no routing
    - no model calls
    """

    def __init__(
        self,
        feedback_builder: LearningFeedbackBuilder | None = None,
    ):
        self.feedback_builder = (
            feedback_builder or LearningFeedbackBuilder()
        )

    def capture(
        self,
        *,
        task: str,
        strategy: str,
        repair_success: bool,
        verification_success: bool,
        attempts: int = 1,
        repair_score: float = 0.0,
        verification_score: float = 0.0,
        retried: bool = False,
        rolled_back: bool = False,
        metadata: str = "",
    ) -> CapturedOutcome:
        if not task.strip():
            raise ValueError("task must not be empty")

        feedback = self.feedback_builder.build(
            task=task,
            strategy=strategy,
            repair_success=repair_success,
            verification_success=verification_success,
            attempts=attempts,
            repair_score=repair_score,
            verification_score=verification_score,
            retried=retried,
            rolled_back=rolled_back,
            metadata=metadata,
        )

        return CapturedOutcome(
            task=task.strip(),
            strategy=strategy.strip(),
            feedback=feedback,
            captured=True,
        )
