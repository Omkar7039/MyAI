from dataclasses import dataclass

from core.tool_decision_engine import (
    ToolDecisionEngine,
    ToolDecisionResult,
)


@dataclass(frozen=True)
class ToolExecutionPlanResult:
    decision: ToolDecisionResult
    execution: object | None
    executed: bool


class ToolPlanExecutor:
    def __init__(
        self,
        orchestrator,
        *,
        decision_engine: ToolDecisionEngine | None = None,
    ):
        self.orchestrator = orchestrator
        self.decision_engine = (
            decision_engine or ToolDecisionEngine()
        )

    def execute(self, request: str) -> ToolExecutionPlanResult:
        decision = self.decision_engine.decide(request)

        if (
            decision.decision is None
            or decision.arguments is None
        ):
            return ToolExecutionPlanResult(
                decision=decision,
                execution=None,
                executed=False,
            )

        tool_name = decision.decision.tool_name
        arguments = decision.arguments.arguments

        try:
            execution = self.orchestrator.invoke_tool(
                tool_name,
                **arguments,
            )

            if (
                tool_name == "read_file"
                and getattr(execution, "success", False)
                and isinstance(getattr(execution, "result", None), str)
            ):
                from tools.base import ToolResult

                execution = ToolResult(
                    tool_name=execution.tool_name,
                    success=execution.success,
                    result={
                        "path": arguments.get("path"),
                        "content": execution.result,
                    },
                    error=execution.error,
                )

        except PermissionError:
            return ToolExecutionPlanResult(
                decision=decision,
                execution=None,
                executed=False,
            )

        return ToolExecutionPlanResult(
            decision=decision,
            execution=execution,
            executed=True,
        )
