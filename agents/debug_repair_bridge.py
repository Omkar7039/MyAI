from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DebugRepairRequest:
    problem: str
    hypothesis: str
    evidence: tuple[str, ...]


class DebugRepairBridge:
    def build_request(self, evidence, hypothesis) -> DebugRepairRequest:
        description = getattr(
            hypothesis,
            "description",
            str(hypothesis),
        )

        return DebugRepairRequest(
            problem=evidence.problem,
            hypothesis=description,
            evidence=tuple(
                getattr(hypothesis, "evidence", ())
            ),
        )

    def build_prompt(self, request: DebugRepairRequest) -> str:
        evidence = "\n".join(
            f"- {item}"
            for item in request.evidence
        )

        return (
            "Repair the code using only the verified debugging hypothesis.\n\n"
            f"Original problem:\n{request.problem}\n\n"
            f"Verified hypothesis:\n{request.hypothesis}\n\n"
            f"Supporting evidence:\n{evidence}\n\n"
            "Make the smallest correct change.\n"
            "Do not change unrelated behavior.\n"
            "Verification must determine whether the repair is actually correct."
        )
