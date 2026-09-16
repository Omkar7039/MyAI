from __future__ import annotations

from dataclasses import dataclass

from experience.learning_signal import (
    LearningSignal,
    LearningSignalType,
)


@dataclass(frozen=True)
class VerificationOutcomeScore:
    score: float
    successful: bool
    strategy_bonus: float
    attempts_penalty: float
    retry_penalty: float
    failure_penalty: float
    reasons: tuple[str, ...]


class VerificationOutcomeScorer:
    """
    Convert verification learning signals into a normalized 0–100 score.

    Base:
      successful verification  +70
      failed verification       0

    Strategy bonus:
      property / mutation       +20
      standard / strengthen     +10

    Penalties:
      extra attempts            -10 each, capped at -20
      retry signal              -10
      failed verification       -20
    """

    STRONG_STRATEGIES = {"property", "mutation"}
    NORMAL_STRATEGIES = {"standard", "strengthen"}

    def score(
        self,
        signals: tuple[LearningSignal, ...]
        | list[LearningSignal],
    ) -> VerificationOutcomeScore:
        verification_signals = [
            signal
            for signal in signals
            if signal.signal_type
            in {
                LearningSignalType.VERIFICATION_SUCCESS,
                LearningSignalType.VERIFICATION_FAILURE,
            }
        ]

        retry_signals = [
            signal
            for signal in signals
            if signal.signal_type == LearningSignalType.RETRY
        ]

        if not verification_signals:
            return VerificationOutcomeScore(
                score=0.0,
                successful=False,
                strategy_bonus=0.0,
                attempts_penalty=0.0,
                retry_penalty=0.0,
                failure_penalty=0.0,
                reasons=("no verification outcome was recorded",),
            )

        latest = verification_signals[-1]

        successful = (
            latest.signal_type
            == LearningSignalType.VERIFICATION_SUCCESS
        )

        score = 70.0 if successful else 0.0
        reasons: list[str] = []

        strategy = latest.strategy.strip().lower()

        if strategy in self.STRONG_STRATEGIES:
            strategy_bonus = 20.0
            reasons.append(
                f"verification used strong strategy {strategy!r}"
            )
        elif strategy in self.NORMAL_STRATEGIES:
            strategy_bonus = 10.0
            reasons.append(
                f"verification used strategy {strategy!r}"
            )
        else:
            strategy_bonus = 0.0

        attempts = max(
            [signal.attempts for signal in verification_signals] or [1]
        )

        attempts_penalty = min(
            max(attempts - 1, 0) * 10.0,
            20.0,
        )

        if attempts_penalty:
            reasons.append(
                f"verification required {attempts} attempts"
            )

        retry_penalty = 10.0 if retry_signals else 0.0

        if retry_penalty:
            reasons.append("verification required a retry")

        failure_penalty = 20.0 if not successful else 0.0

        if failure_penalty:
            reasons.append("verification failed")
        else:
            reasons.append("verification passed")

        score = max(
            0.0,
            min(
                100.0,
                score
                + strategy_bonus
                - attempts_penalty
                - retry_penalty
                - failure_penalty,
            ),
        )

        return VerificationOutcomeScore(
            score=score,
            successful=successful,
            strategy_bonus=strategy_bonus,
            attempts_penalty=attempts_penalty,
            retry_penalty=retry_penalty,
            failure_penalty=failure_penalty,
            reasons=tuple(reasons),
        )
