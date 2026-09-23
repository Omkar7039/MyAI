from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from core.tool_next_decision import NextDecision, ToolNextDecisionEngine
from core.tool_result_observer import ToolObservation, ToolResultObserver


@dataclass(frozen=True)
class ToolAgentStepResult:
    execution_plan: object
    observation: ToolObservation
    next_decision: NextDecision


class ToolAgentStep:
    """
    Executes exactly one bounded tool-agent step.

    Flow:

        request
            ↓
        executor
            ↓
        ToolResultObserver
            ↓
        ToolNextDecisionEngine

    This component deliberately does not implement a loop.
    """

    def __init__(
        self,
        executor: Callable[[str], object],
        observer: ToolResultObserver | None = None,
        next_decision_engine: ToolNextDecisionEngine | None = None,
    ) -> None:
        self._executor = executor
        self._observer = observer or ToolResultObserver()
        self._next_decision_engine = (
            next_decision_engine or ToolNextDecisionEngine()
        )

    def run(self, request: str) -> ToolAgentStepResult:
        execution_plan = self._executor(request)

        observation = self._observer.observe(execution_plan)

        next_decision = self._next_decision_engine.decide(
            request,
            observation,
        )

        return ToolAgentStepResult(
            execution_plan=execution_plan,
            observation=observation,
            next_decision=next_decision,
        )
