from __future__ import annotations

from dataclasses import dataclass

from experience.learning_control import LearningControlAdapter
from experience.learning_feedback import (
    LearningFeedback,
    LearningFeedbackBuilder,
)
from experience.learning_signal import LearningSignal


@dataclass(frozen=True)
class LearningFeedbackIntegrationResult:
    feedback: LearningFeedback
    signals: tuple[LearningSignal, ...]
    ready_for_learning: bool


class AutomaticLearningFeedback:
    """
    Convert concrete repair/verification outcomes into learning-ready
    feedback without persisting anything or changing the outcome itself.
    """

    def __init__(
        self,
        builder: LearningFeedbackBuilder | None = None,
        control: LearningControlAdapter | None = None,
    ):
        self.builder = builder or LearningFeedbackBuilder()
        self.control = control

    def process(
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
        baseline_score: float | None = None,
        learned_score: float | None = None,
    ) -> LearningFeedbackIntegrationResult:
        feedback = self.builder.build(
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

        signals = list(feedback.signals)

        if (
            self.control is not None
            and baseline_score is not None
            and learned_score is not None
        ):
            control_decision = self.control.evaluate(
                strategy=feedback.strategy,
                baseline_score=baseline_score,
                learned_score=learned_score,
            )

            if control_decision.rollback and not rolled_back:
                signals.append(
                    self.builder.collector.rollback(
                        task,
                        strategy=feedback.strategy,
                        attempts=attempts,
                        score=feedback.score,
                        metadata=metadata,
                    )
                )

        final_signals = tuple(signals)

        return LearningFeedbackIntegrationResult(
            feedback=feedback,
            signals=final_signals,
            ready_for_learning=bool(final_signals),
        )
