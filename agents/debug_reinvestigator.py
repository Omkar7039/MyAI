from __future__ import annotations

from dataclasses import dataclass

from agents.debug_investigation import DebugInvestigator


@dataclass(frozen=True)
class DebugReinvestigationResult:
    original: object
    final: object
    resolved: bool
    reason: str


class DebugReinvestigator:
    def __init__(self, investigator: DebugInvestigator | None = None):
        self.investigator = investigator or DebugInvestigator()

    def verify_repair(
        self,
        original,
        repaired_code: str,
    ) -> DebugReinvestigationResult:
        final = self.investigator.investigate(
            problem=original.problem,
            code=repaired_code,
            error=original.error,
            language=original.language,
        )

        resolved = self._resolved(
            original,
            final,
        )

        if resolved:
            reason = "Original debugging failure is no longer reproduced."
        else:
            reason = "Original debugging failure is still reproduced or remains unverified."

        return DebugReinvestigationResult(
            original=original,
            final=final,
            resolved=resolved,
            reason=reason,
        )

    @staticmethod
    def _resolved(original, final) -> bool:
        if final.timed_out:
            return False

        if original.runtime_failed:
            return final.runtime_success

        if original.runtime_success:
            return final.runtime_success

        return (
            original.runtime_available
            and not final.runtime_failed
        )
