from __future__ import annotations

from tools.base import ToolResult
from tools.runner_manager import RunnerManager


class ExecutionTool:
    """
    Explicit code-execution tool backed by RunnerManager.
    """

    name = "execute_code"
    description = (
        "Execute supported source code through the controlled runner layer."
    )

    def __init__(
        self,
        runner_manager: RunnerManager | None = None,
    ):
        self.runner_manager = (
            runner_manager or RunnerManager()
        )

    def execute(
        self,
        code: str,
        language: str,
    ) -> ToolResult:
        try:
            if not code.strip():
                raise ValueError(
                    "No code supplied for execution."
                )

            normalized = language.strip().lower()

            if not normalized or normalized == "unknown":
                raise ValueError(
                    "Cannot execute code because "
                    "the language is unknown."
                )

            if not self.runner_manager.supports(normalized):
                raise ValueError(
                    f"No execution runner is installed for: "
                    f"{language}"
                )

            result = self.runner_manager.run(
                normalized,
                code,
            )

            return ToolResult(
                tool_name=self.name,
                success=True,
                result=result,
            )

        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=str(exc),
            )
