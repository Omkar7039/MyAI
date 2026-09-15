from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryContext:
    attempt: int
    previous_stage: str
    previous_errors: tuple[str, ...]
    previous_rolled_back: bool

    def render(self) -> str:
        lines = [
            f"Previous attempt: {self.attempt}",
            f"Previous stage: {self.previous_stage}",
            f"Previous rollback: {self.previous_rolled_back}",
        ]

        if self.previous_errors:
            lines.append("Previous errors:")
            lines.extend(
                f"- {error}"
                for error in self.previous_errors
            )

        return "\n".join(lines)


class AutonomousMultiFileRetryPlanner:
    def build_request(self, request: str, retry_context: RetryContext | None = None):
        if retry_context is None:
            return request

        return (
            f"{request}\n\n"
            "AUTONOMOUS RETRY CONTEXT:\n"
            f"{retry_context.render()}\n\n"
            "Use the previous failure to improve the next repair plan. "
            "Do not blindly repeat the failed approach."
        )
