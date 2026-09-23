from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tools.result_normalizer import ToolResultNormalizer


@dataclass(frozen=True)
class ToolObservation:
    tool_name: str | None
    success: bool
    result: Any = None
    error: str | None = None
    executed: bool = False


class ToolResultObserver:
    """
    Observe and normalize a ToolPlanExecutor result without executing anything.

    The observer:
    - does not execute tools
    - does not choose another tool
    - does not modify tool implementations
    - preserves the existing execution result contract
    """

    def __init__(
        self,
        normalizer: ToolResultNormalizer | None = None,
    ) -> None:
        self._normalizer = normalizer or ToolResultNormalizer()

    def observe(self, execution_plan: object) -> ToolObservation:
        decision_result = getattr(execution_plan, "decision", None)
        execution = getattr(execution_plan, "execution", None)
        executed = bool(getattr(execution_plan, "executed", False))

        decision = getattr(decision_result, "decision", None)
        tool_name = getattr(decision, "tool_name", None)

        # Nothing was executed.
        if execution is None:
            return ToolObservation(
                tool_name=tool_name,
                success=False,
                result=None,
                error=None,
                executed=False,
            )

        execution_tool_name = getattr(execution, "tool_name", None)
        if execution_tool_name is not None:
            tool_name = execution_tool_name

        success = bool(getattr(execution, "success", False))
        error = getattr(execution, "error", None)

        # Normalize the COMPLETE execution result, not execution.result.
        #
        # ToolResultNormalizer represents ToolResult as an envelope such as:
        #
        # {
        #     "tool_name": "...",
        #     "success": True,
        #     "result": ...,
        #     "error": None,
        # }
        #
        # Extract the payload from that normalized envelope at the observer
        # boundary.
        normalized_execution = self._normalize(execution)

        if isinstance(normalized_execution, dict):
            has_tool_result_shape = (
                "tool_name" in normalized_execution
                and "success" in normalized_execution
                and "result" in normalized_execution
                and "error" in normalized_execution
            )

            if has_tool_result_shape:
                normalized_tool_name = normalized_execution.get("tool_name")
                if normalized_tool_name is not None:
                    tool_name = normalized_tool_name

                success = bool(normalized_execution.get("success", success))
                error = normalized_execution.get("error", error)
                normalized_result = normalized_execution.get("result")
            else:
                normalized_result = normalized_execution
        else:
            normalized_result = normalized_execution

        return ToolObservation(
            tool_name=tool_name,
            success=success,
            result=normalized_result,
            error=error,
            executed=executed,
        )

    def _normalize(self, value: Any) -> Any:
        return self._normalizer.normalize(value)
