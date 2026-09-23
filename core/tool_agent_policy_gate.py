from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from core.tool_agent_instruction_validator import ValidatedToolInstruction


@dataclass(frozen=True)
class PolicyCheckedToolInstruction:
    instruction: ValidatedToolInstruction
    allowed: bool
    reason: str


class ToolAgentPolicyGate:
    def __init__(
        self,
        permission_checker: Callable[[str], bool],
    ) -> None:
        if not callable(permission_checker):
            raise TypeError(
                "permission_checker must be callable."
            )

        self._permission_checker = permission_checker

    def check(
        self,
        instruction: ValidatedToolInstruction,
    ) -> PolicyCheckedToolInstruction:
        if not isinstance(
            instruction,
            ValidatedToolInstruction,
        ):
            raise TypeError(
                "instruction must be a ValidatedToolInstruction."
            )

        model_instruction = instruction.instruction

        if model_instruction.action in {"complete", "stop"}:
            return PolicyCheckedToolInstruction(
                instruction=instruction,
                allowed=True,
                reason="No tool execution is requested.",
            )

        tool_name = model_instruction.tool_name

        if tool_name is None:
            return PolicyCheckedToolInstruction(
                instruction=instruction,
                allowed=False,
                reason="Tool execution requires a tool name.",
            )

        allowed = bool(self._permission_checker(tool_name))

        if allowed:
            reason = f"Tool '{tool_name}' is permitted by the policy authority."
        else:
            reason = f"Tool '{tool_name}' is blocked by the policy authority."

        return PolicyCheckedToolInstruction(
            instruction=instruction,
            allowed=allowed,
            reason=reason,
        )
