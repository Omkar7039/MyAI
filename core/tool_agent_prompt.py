from __future__ import annotations

from core.tool_agent_context import ToolAgentContext
from core.tool_agent_context_formatter import ToolAgentContextFormatter


class ToolAgentPromptBuilder:
    """
    Builds a deterministic prompt for future model-driven tool reasoning.

    This class does not:
    - call the model
    - execute tools
    - select tools
    - modify session state
    """

    SYSTEM_INSTRUCTIONS = (
        "You are MyAI's tool-reasoning component.\n"
        "Use the supplied request and tool execution context to reason "
        "about the current task.\n"
        "Do not assume a tool was executed unless the context says it was.\n"
        "Respect execution failures and policy-related non-execution.\n"
        "When the current work is complete, indicate completion.\n"
        "When another step is explicitly required, indicate continuation.\n"
        "Do not invent tool results."
    )

    def __init__(
        self,
        formatter: ToolAgentContextFormatter | None = None,
    ) -> None:
        self._formatter = formatter or ToolAgentContextFormatter()

    def build(
        self,
        request: str,
        context: ToolAgentContext,
    ) -> str:
        if not isinstance(request, str):
            raise TypeError("request must be a string.")

        formatted_context = self._formatter.to_text(context)

        return (
            f"{self.SYSTEM_INSTRUCTIONS}\n\n"
            f"USER REQUEST:\n"
            f"{request}\n\n"
            f"TOOL EXECUTION CONTEXT:\n"
            f"{formatted_context}"
        )
