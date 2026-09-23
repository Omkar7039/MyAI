from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal


ModelAction = Literal["complete", "continue", "stop"]


@dataclass(frozen=True)
class ModelToolInstruction:
    action: ModelAction
    reason: str
    tool_name: str | None
    raw_response: str


class ToolAgentModelParser:
    ALLOWED_ACTIONS = frozenset({"complete", "continue", "stop"})
    ALLOWED_FIELDS = frozenset({"action", "reason", "tool_name"})

    def parse(self, response: str) -> ModelToolInstruction:
        if not isinstance(response, str):
            raise TypeError("response must be a string.")

        raw_response = response
        payload = self._decode(response)

        if not isinstance(payload, dict):
            raise ValueError("Model response must be a JSON object.")

        unknown_fields = set(payload) - self.ALLOWED_FIELDS
        if unknown_fields:
            raise ValueError(
                "Model response contains unsupported fields: "
                + ", ".join(sorted(unknown_fields))
            )

        action = payload.get("action")
        reason = payload.get("reason")
        tool_name = payload.get("tool_name")

        if action not in self.ALLOWED_ACTIONS:
            raise ValueError(
                "action must be one of: complete, continue, stop."
            )

        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("reason must be a non-empty string.")

        if tool_name is not None:
            if not isinstance(tool_name, str):
                raise ValueError("tool_name must be a string or null.")

            tool_name = tool_name.strip() or None

        if action != "continue" and tool_name is not None:
            raise ValueError(
                "tool_name is only allowed when action is continue."
            )

        return ModelToolInstruction(
            action=action,
            reason=reason.strip(),
            tool_name=tool_name,
            raw_response=raw_response,
        )

    def _decode(self, response: str) -> object:
        text = response.strip()

        if not text:
            raise ValueError("Model response is empty.")

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        if text.startswith("```") and text.endswith("```"):
            lines = text.splitlines()

            if len(lines) >= 3:
                opening = lines[0].strip().lower()

                if opening in {"```json", "```"}:
                    fenced = "\n".join(lines[1:-1]).strip()

                    try:
                        return json.loads(fenced)
                    except json.JSONDecodeError as exc:
                        raise ValueError(
                            "Model response contains invalid JSON."
                        ) from exc

        raise ValueError("Model response must contain valid JSON.")
