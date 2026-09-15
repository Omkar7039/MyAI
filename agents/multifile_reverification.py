from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MultiFileReverificationResult:
    verified: bool
    rolled_back: bool
    stage: str
    errors: tuple[str, ...]
    reason: str


class MultiFileReverification:
    def verify(self, result) -> MultiFileReverificationResult:
        success = bool(result.get("success", False))
        rolled_back = bool(result.get("rolled_back", False))
        stage = str(result.get("stage", "unknown"))

        errors = tuple(
            str(error)
            for error in result.get("errors", [])
        )

        if success:
            return MultiFileReverificationResult(
                verified=True,
                rolled_back=rolled_back,
                stage=stage,
                errors=errors,
                reason="Multi-file repair passed post-repair verification.",
            )

        if rolled_back:
            return MultiFileReverificationResult(
                verified=False,
                rolled_back=True,
                stage=stage,
                errors=errors,
                reason="Multi-file repair failed verification and was rolled back.",
            )

        return MultiFileReverificationResult(
            verified=False,
            rolled_back=False,
            stage=stage,
            errors=errors,
            reason="Multi-file repair could not be verified.",
        )
