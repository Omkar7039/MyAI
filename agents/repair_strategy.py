from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RepairStrategyDecision:
    requested: str
    applied: str
    fallback: bool
    reason: str


class RepairStrategyExecutor:
    """
    Resolve governed repair strategies to executable strategies.

    The existing repair implementation is the only executable
    strategy at this stage. Future specialized strategies can be
    added here without changing RepairAgent's public API.
    """

    STANDARD = "standard"

    def resolve(self, strategy: str) -> RepairStrategyDecision:
        requested = strategy.strip().lower()

        if not requested:
            raise ValueError("strategy must not be empty")

        if requested == self.STANDARD:
            return RepairStrategyDecision(
                requested=requested,
                applied=self.STANDARD,
                fallback=False,
                reason="standard repair strategy selected",
            )

        return RepairStrategyDecision(
            requested=requested,
            applied=self.STANDARD,
            fallback=True,
            reason=(
                f"repair strategy {requested!r} is not implemented; "
                "using standard repair"
            ),
        )
