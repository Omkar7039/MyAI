from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RepairImprovement:
    strategy: str
    constraints: tuple[str, ...]
    reason: str


class MultiFileRepairImprovementPlanner:
    def plan(self, attempt_result) -> RepairImprovement:
        stage = str(
            attempt_result.get("stage", "unknown")
        ).lower()

        errors = tuple(
            str(error)
            for error in attempt_result.get("errors", [])
        )

        rolled_back = bool(
            attempt_result.get("rolled_back", False)
        )

        if stage == "planning":
            return RepairImprovement(
                strategy="Reconsider affected files and produce a new minimal patch plan.",
                constraints=(
                    "Do not repeat the failed planning approach.",
                    "Keep the patch limited to files supported by evidence.",
                ),
                reason="The previous repair failed during planning.",
            )

        if stage == "validation":
            return RepairImprovement(
                strategy="Reduce the patch and correct the validation failure.",
                constraints=(
                    "Do not apply an invalid patch.",
                    "Preserve unrelated source code.",
                ),
                reason="The previous patch did not pass validation.",
            )

        if stage == "post_apply_verification":
            rollback_constraint = (
                "A previous patch was rolled back."
                if rolled_back
                else "Previous post-apply verification failed."
            )

            return RepairImprovement(
                strategy="Change the repair approach and target the verified failure.",
                constraints=(
                    rollback_constraint,
                    "The next patch must satisfy post-apply verification.",
                    "Do not blindly repeat the previous patch.",
                ),
                reason="The previous repair failed after application.",
            )

        if errors:
            return RepairImprovement(
                strategy="Use the reported failure evidence to revise the repair.",
                constraints=(
                    "Address the reported errors before introducing unrelated changes.",
                ),
                reason="The previous attempt returned execution errors.",
            )

        return RepairImprovement(
            strategy="Stop and gather stronger evidence before another repair.",
            constraints=(
                "Do not repeat an unsupported repair attempt.",
            ),
            reason="There is not enough evidence to improve the repair safely.",
        )

    def build_directive(self, improvement: RepairImprovement) -> str:
        constraints = "\n".join(
            f"- {item}"
            for item in improvement.constraints
        )

        return (
            "AUTONOMOUS REPAIR IMPROVEMENT:\n"
            f"Strategy: {improvement.strategy}\n"
            f"Reason: {improvement.reason}\n"
            "Constraints:\n"
            f"{constraints}"
        )
