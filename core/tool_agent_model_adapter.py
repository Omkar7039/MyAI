from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ModelReasoningResult:
    prompt: str
    response: str
    raw_response: Any


class ToolAgentModelAdapter:
    """
    Thin boundary between tool-agent reasoning and the local model.

    The adapter only generates model output.

    It does not:
    - execute tools
    - select tools
    - modify session state
    - invoke the orchestrator
    """

    def __init__(
        self,
        generator: Callable[[str], Any],
    ) -> None:
        if not callable(generator):
            raise TypeError("generator must be callable.")

        self._generator = generator

    def generate(self, prompt: str) -> ModelReasoningResult:
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a string.")

        raw_response = self._generator(prompt)

        if isinstance(raw_response, str):
            response = raw_response
        else:
            response = str(raw_response)

        return ModelReasoningResult(
            prompt=prompt,
            response=response,
            raw_response=raw_response,
        )
