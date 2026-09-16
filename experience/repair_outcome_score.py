from __future__ import annotations

from dataclasses import dataclass

from experience.learning_signal import (
    LearningSignal,
    LearningSignalType,
)


@dataclass(frozen=True)
class RepairOutcomeScore:
    score: float
    successful: bool
    attempts_penalty: float
    verification_bonus: float
    rollback_penalty: float
    reasons: tuple[str, ...]


class RepairOutcomeScorer:
    """
    Convert repair learning signals into a normalized 0–100 score.

    Scoring:
      successful repair:      +70
      successful verification +20
      retry pressure:         -10 per extra attempt, max -20
      rollback:               -30
      failed repair:           0 base
    """

    def score(
        self,
        signals: tuple[LearningSignal, ...] | list[LearningSignal],
    ) -> RepairOutcomeScore:
        repair_signals = [
            signal
            for signal in signals
            if signal.signal_type
            in {
                LearningSignalType.REPAIR_SUCCESS,
                LearningSignalType.REPAIR_FAILURE,
            }
        ]

        verification_signals = [
            signal
            for signal in signals
            if signal.signal_type
            in {
                LearningSignalType.VERIFICATION_SUCCESS,
                LearningSignalType.VERIFICATION_FAILURE,
            }
        ]

        rollback_signals = [
            signal
            for signal in signals
            if signal.signal_type == LearningSignalType.ROLLBACK
        ]

        retry_signals = [
            signal
            for signal in signals
            if signal.signal_type == LearningSignalType.RETRY
        ]

        reasons: list[str] = []

        successful = bool(
            repair_signals
            and repair_signals[-1].signal_type
            == LearningSignalType.REPAIR_SUCCESS
        )

        base = 70.0 if successful else 0.0

        verification_bonus = 0.0

        if verification_signals:
            latest_verification = verification_signals[-1]

            if (
                latest_verification.signal_type
                == LearningSignalType.VERIFICATION_SUCCESS
            ):
                verification_bonus = 20.0
                reasons.append(
                    "repair was successfully verified"
                )
            else:
                verification_bonus = 0.0
                reasons.append(
                    "repair verification failed"
                )

        attempts = max(
            [signal.attempts for signal in signals] or [1]
        )

        attempts_penalty = min(
            max(attempts - 1, 0) * 10.0,
            20.0,
        )

        if attempts_penalty:
            reasons.append(
                f"repair required {attempts} attempts"
            )

        rollback_penalty = 30.0 if rollback_signals else 0.0

        if rollback_penalty:
            reasons.append(
                "repair required rollback"
            )

        if successful:
            reasons.append(
                "repair completed successfully"
            )
        elif repair_signals:
            reasons.append(
                "repair did not complete successfully"
            )
        else:
            reasons.append(
                "no repair outcome was recorded"
            )

        score = max(
            0.0,
            min(
                100.0,
                base
                + verification_bonus
                - attempts_penalty
                - rollback_penalty,
            ),
        )

        return RepairOutcomeScore(
            score=score,
            successful=successful,
            attempts_penalty=attempts_penalty,
            verification_bonus=verification_bonus,
            rollback_penalty=rollback_penalty,
            reasons=tuple(reasons),
        )
