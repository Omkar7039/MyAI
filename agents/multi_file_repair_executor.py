from __future__ import annotations

from pathlib import Path

from agents.multi_file_repair import MultiFileRepairPlanner
from experience.multifile_outcome import MultiFileRepairOutcomeRecorder
from project.patch_applier import PatchApplier


class MultiFileRepairExecutor:
    """Execute a planned multi-file repair and record its real outcome."""

    def __init__(
        self,
        planner: MultiFileRepairPlanner | None = None,
        applier: PatchApplier | None = None,
        outcome_recorder: MultiFileRepairOutcomeRecorder | None = None,
        root: str = "~/MyAI",
    ):
        self.root = Path(root).expanduser().resolve()
        self.planner = planner or MultiFileRepairPlanner(
            root=self.root
        )
        self.applier = applier or PatchApplier(
            root=self.root
        )
        self.outcome_recorder = (
            outcome_recorder
            or MultiFileRepairOutcomeRecorder()
        )

    def execute(
        self,
        request: str,
        plan,
        evidence: str,
        model_response=None,
        record_experience: bool = True,
    ):
        patch_result = self.planner.build_patch_set(
            request=request,
            plan=plan,
            evidence=evidence,
            model_response=model_response,
        )

        if not patch_result["success"]:
            result = {
                "success": False,
                "stage": "patch_planning",
                "errors": patch_result.get("errors", []),
                "warnings": patch_result.get("warnings", []),
                "applied_files": [],
                "rolled_back": False,
            }

            if record_experience:
                self._record(
                    request=request,
                    plan=plan,
                    result=result,
                )

            return result

        apply_result = self.applier.apply(
            patch_result["patch_set"]
        )

        result = {
            "success": apply_result["success"],
            "stage": apply_result["stage"],
            "errors": apply_result["errors"],
            "warnings": apply_result["warnings"],
            "applied_files": apply_result["applied_files"],
            "rolled_back": apply_result["rolled_back"],
        }

        if record_experience:
            self._record(
                request=request,
                plan=plan,
                result=result,
            )

        return result

    def _record(
        self,
        request,
        plan,
        result,
    ):
        try:
            self.outcome_recorder.record(
                request=request,
                plan=plan,
                result=result,
                project_root=str(self.root),
            )
        except Exception:
            # Learning must never break repair execution.
            pass
