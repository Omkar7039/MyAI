from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class RecoveryThrottleResult:
    allowed: bool
    elapsed: float
    remaining: float
    reason: str


class RuntimeRecoveryThrottle:
    """
    Prevent rapid repeated automatic recovery for the same fingerprint.

    The throttle is intentionally in-memory and uses monotonic time.
    It never sleeps or executes recovery.
    """

    def __init__(
        self,
        *,
        cooldown_seconds: float = 5.0,
        clock: Callable[[], float] | None = None,
    ):
        if cooldown_seconds < 0:
            raise ValueError(
                "cooldown_seconds must be >= 0"
            )

        self.cooldown_seconds = float(cooldown_seconds)
        self._clock = clock or time.monotonic
        self._last_attempt: dict[str, float] = {}

    @staticmethod
    def _normalize_fingerprint(
        fingerprint: str,
    ) -> str:
        value = fingerprint.strip()

        if not value:
            raise ValueError(
                "fingerprint must not be empty"
            )

        return value

    def check(
        self,
        fingerprint: str,
    ) -> RecoveryThrottleResult:
        key = self._normalize_fingerprint(
            fingerprint
        )

        now = self._clock()
        last = self._last_attempt.get(key)

        if last is None:
            return RecoveryThrottleResult(
                allowed=True,
                elapsed=0.0,
                remaining=0.0,
                reason="no previous recovery attempt",
            )

        elapsed = max(
            0.0,
            now - last,
        )

        remaining = max(
            0.0,
            self.cooldown_seconds - elapsed,
        )

        if remaining > 0:
            return RecoveryThrottleResult(
                allowed=False,
                elapsed=elapsed,
                remaining=remaining,
                reason=(
                    f"recovery cooldown active for {key}"
                ),
            )

        return RecoveryThrottleResult(
            allowed=True,
            elapsed=elapsed,
            remaining=0.0,
            reason="recovery cooldown elapsed",
        )

    def record(
        self,
        fingerprint: str,
    ) -> RecoveryThrottleResult:
        key = self._normalize_fingerprint(
            fingerprint
        )

        now = self._clock()
        previous = self._last_attempt.get(key)

        self._last_attempt[key] = now

        if previous is None:
            return RecoveryThrottleResult(
                allowed=True,
                elapsed=0.0,
                remaining=self.cooldown_seconds,
                reason="recovery attempt recorded",
            )

        elapsed = max(
            0.0,
            now - previous,
        )

        return RecoveryThrottleResult(
            allowed=True,
            elapsed=elapsed,
            remaining=self.cooldown_seconds,
            reason="recovery attempt recorded",
        )

    def reset(
        self,
        fingerprint: str,
    ) -> None:
        key = self._normalize_fingerprint(
            fingerprint
        )
        self._last_attempt.pop(key, None)

    def clear(self) -> None:
        self._last_attempt.clear()

    def last_attempt(
        self,
        fingerprint: str,
    ) -> float | None:
        key = self._normalize_fingerprint(
            fingerprint
        )
        return self._last_attempt.get(key)
