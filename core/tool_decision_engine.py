from dataclasses import dataclass

from core.tool_argument_extractor import (
    ToolArgumentExtractor,
    ToolArguments,
)
from core.tool_planner import ToolDecision, ToolPlanner


@dataclass(frozen=True)
class ToolDecisionResult:
    decision: ToolDecision | None
    arguments: ToolArguments | None


class ToolDecisionEngine:
    def __init__(
        self,
        *,
        planner: ToolPlanner | None = None,
        argument_extractor: ToolArgumentExtractor | None = None,
    ):
        self.planner = planner or ToolPlanner()
        self.argument_extractor = (
            argument_extractor or ToolArgumentExtractor()
        )

    def decide(self, request: str) -> ToolDecisionResult:
        if not isinstance(request, str):
            raise TypeError("request must be a string.")

        request = request.strip()

        if not request:
            return ToolDecisionResult(
                decision=None,
                arguments=None,
            )

        decision = self.planner.plan(request)

        if decision is None:
            return ToolDecisionResult(
                decision=None,
                arguments=None,
            )

        arguments = self.argument_extractor.extract(
            decision.tool_name,
            request,
        )

        return ToolDecisionResult(
            decision=decision,
            arguments=arguments,
        )
