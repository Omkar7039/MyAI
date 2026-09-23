from __future__ import annotations

from dataclasses import dataclass

from core.tool_agent_model_parser import ModelToolInstruction


@dataclass(frozen=True)
class ValidatedToolInstruction:
    instruction: ModelToolInstruction


class ToolAgentInstructionValidator:
    """
    Validates a parsed model instruction against a known tool set.

    This component:
    - validates tool existence
    - validates that continuation has a tool
    - preserves the parsed instruction

    It does not:
    - execute tools
    - invoke the orchestrator
    - apply execution policy
    - modify session state
    """

    def __init__(self, allowed_tools: set[str] | frozenset[str]):
        if not isinstance(allowed_tools, (set, frozenset)):
            raise TypeError(
                "allowed_tools must be a set or frozenset."
            )

        self._allowed_tools = frozenset(
            self._normalize_tool_name(name)
            for name in allowed_tools
        )

    @property
    def allowed_tools(self) -> frozenset[str]:
        return self._allowed_tools

    def validate(
        self,
        instruction: ModelToolInstruction,
    ) -> ValidatedToolInstruction:
        if not isinstance(
            instruction,
            ModelToolInstruction,
        ):
            raise TypeError(
                "instruction must be a ModelToolInstruction."
            )

        if instruction.action == "continue":
            if instruction.tool_name is None:
                raise ValueError(
                    "continue action requires tool_name."
                )

            normalized_name = self._normalize_tool_name(
                instruction.tool_name
            )

            if normalized_name not in self._allowed_tools:
                raise ValueError(
                    f"Unknown tool: {instruction.tool_name}."
                )

            if normalized_name != instruction.tool_name:
                instruction = ModelToolInstruction(
                    action=instruction.action,
                    reason=instruction.reason,
                    tool_name=normalized_name,
                    raw_response=instruction.raw_response,
                )

        elif instruction.tool_name is not None:
            raise ValueError(
                "tool_name is only allowed when action is continue."
            )

        return ValidatedToolInstruction(
            instruction=instruction,
        )

    @staticmethod
    def _normalize_tool_name(name: str) -> str:
        if not isinstance(name, str):
            raise TypeError("tool name must be a string.")

        normalized = name.strip().lower()

        if not normalized:
            raise ValueError("tool name must not be empty.")

        return normalized
