from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecoveryGuardResult:
    allowed: bool
    attempts: int
    remaining: int
    reason: str


class RuntimeRecoveryGuard:
    """
    Bound automatic recovery attempts and prevent identical recovery loops.

    The guard does not execute recovery. It only decides whether another
    automatic recovery attempt is permitted.
    """

    def __init__(
        self,
        *,
        max_attempts: int = 3,
    ):
        if max_attempts < 0:
            raise ValueError("max_attempts must be >= 0")

        self.max_attempts = max_attempts
        self._attempts: dict[str, int] = {}

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
    ) -> RecoveryGuardResult:
        key = self._normalize_fingerprint(fingerprint)
        attempts = self._attempts.get(key, 0)

        if attempts >= self.max_attempts:
            return RecoveryGuardResult(
                allowed=False,
                attempts=attempts,
                remaining=0,
                reason=(
                    "automatic recovery attempt limit reached "
                    f"for {key}"
                ),
            )

        return RecoveryGuardResult(
            allowed=True,
            attempts=attempts,
            remaining=self.max_attempts - attempts,
            reason="automatic recovery attempt is allowed",
        )

    def record(
        self,
        fingerprint: str,
    ) -> RecoveryGuardResult:
        key = self._normalize_fingerprint(fingerprint)

        current = self._attempts.get(key, 0)

        if current >= self.max_attempts:
            return RecoveryGuardResult(
                allowed=False,
                attempts=current,
                remaining=0,
                reason=(
                    "automatic recovery attempt limit already reached "
                    f"for {key}"
                ),
            )

        attempts = current + 1
        self._attempts[key] = attempts

        return RecoveryGuardResult(
            allowed=True,
            attempts=attempts,
            remaining=self.max_attempts - attempts,
            reason="automatic recovery attempt recorded",
        )

    def reset(
        self,
        fingerprint: str,
    ) -> None:
        key = self._normalize_fingerprint(fingerprint)
        self._attempts.pop(key, None)

    def clear(self) -> None:
        self._attempts.clear()

    def attempts(
        self,
        fingerprint: str,
    ) -> int:
        key = self._normalize_fingerprint(fingerprint)
        return self._attempts.get(key, 0)
