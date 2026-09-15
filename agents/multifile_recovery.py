from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MultiFileRecoveryResult:
    safe_to_continue: bool
    rolled_back: bool
    reason: str


class MultiFileRecoveryManager:
    def evaluate(self, result) -> MultiFileRecoveryResult:
        success = bool(result.get("success", False))
        rolled_back = bool(result.get("rolled_back", False))

        if success:
            return MultiFileRecoveryResult(
                safe_to_continue=True,
                rolled_back=rolled_back,
                reason="Repair completed successfully; workspace is safe to continue.",
            )

        if rolled_back:
            return MultiFileRecoveryResult(
                safe_to_continue=True,
                rolled_back=True,
                reason="Repair failed but rollback completed; workspace was restored.",
            )

        return MultiFileRecoveryResult(
            safe_to_continue=False,
            rolled_back=False,
            reason="Repair failed without confirmed rollback; workspace requires recovery before retry.",
        )
