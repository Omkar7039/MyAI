from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from core.tool_result_observer import ToolObservation


NextAction = Literal["complete", "continue", "stop"]


@dataclass(frozen=True)
class NextDecision:
    action: NextAction
    reason: str
    tool_name: str | None = None


class ToolNextDecisionEngine:
    """
    Deterministically evaluates whether tool processing should stop
    or continue to another reasoning step.

    This component never selects or executes a tool.
    """

    _FOLLOW_UP_MARKERS = (
        " and then ",
        " then ",
        " after that ",
        " next ",
        " also ",
        " and verify ",
        " then verify ",
        " and check ",
        " then check ",
        " and fix ",
        " then fix ",
    )

    def decide(
        self,
        request: str,
        observation: ToolObservation,
    ) -> NextDecision:
        tool_name = observation.tool_name

        if not observation.executed:
            return NextDecision(
                action="stop",
                reason="No tool execution occurred.",
                tool_name=tool_name,
            )

        if not observation.success:
            return NextDecision(
                action="stop",
                reason="Tool execution failed; no automatic next action is selected.",
                tool_name=tool_name,
            )

        normalized_request = f" {request.strip().lower()} "

        if any(
            marker in normalized_request
            for marker in self._FOLLOW_UP_MARKERS
        ):
            return NextDecision(
                action="continue",
                reason="The request contains an explicit follow-up step.",
                tool_name=tool_name,
            )

        return NextDecision(
            action="complete",
            reason="The observed tool execution completed successfully with no explicit follow-up step.",
            tool_name=tool_name,
        )
