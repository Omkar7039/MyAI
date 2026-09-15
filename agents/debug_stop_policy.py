from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DebugStopDecision:
    action: str
    reason: str


class DebugStopPolicy:
    def decide(
        self,
        hypothesis_result=None,
        repair_result=None,
        reinvestigation_result=None,
        attempt_count: int = 0,
        max_attempts: int = 3,
    ) -> DebugStopDecision:
        if attempt_count >= max_attempts:
            return DebugStopDecision(
                action="stop",
                reason="Maximum debugging attempts reached.",
            )

        if reinvestigation_result is not None:
            if reinvestigation_result.resolved:
                return DebugStopDecision(
                    action="success",
                    reason="Repair resolved the original debugging failure.",
                )

            return DebugStopDecision(
                action="retry",
                reason="Repair did not resolve the original debugging failure.",
            )

        if repair_result is not None:
            if getattr(repair_result, "success", False):
                return DebugStopDecision(
                    action="reinvestigate",
                    reason="Repair reported success; re-investigation is required.",
                )

            return DebugStopDecision(
                action="retry",
                reason="Repair was not verified successfully.",
            )

        if hypothesis_result is not None:
            if getattr(hypothesis_result, "selected", None) is not None:
                return DebugStopDecision(
                    action="repair",
                    reason="A hypothesis was verified and can be passed to repair.",
                )

            return DebugStopDecision(
                action="stop",
                reason="No hypothesis was verified from available evidence.",
            )

        return DebugStopDecision(
            action="investigate",
            reason="Debugging investigation has not yet started.",
        )
