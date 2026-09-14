from __future__ import annotations

from experience.project_link import ExperienceProjectLink
from experience.project_link_store import ExperienceProjectLinkStore
from experience.provenance import ExperienceProvenance
from experience.recorder import ExperienceRecorder


class MultiFileRepairOutcomeRecorder:
    """Record real multi-file patch outcomes without affecting repair execution."""

    def __init__(
        self,
        recorder: ExperienceRecorder | None = None,
        link_store: ExperienceProjectLinkStore | None = None,
    ):
        self.recorder = recorder or ExperienceRecorder()
        self.link_store = link_store or ExperienceProjectLinkStore()

    def record(
        self,
        request: str,
        plan,
        result: dict,
        project_root: str,
    ):
        success = bool(
            result.get("success")
            and not result.get("rolled_back")
        )

        applied_files = tuple(
            path
            for path in result.get("applied_files", [])
            if path
        )

        target_symbols = tuple(
            target.symbol
            for target in getattr(plan, "targets", [])
            if getattr(target, "symbol", "")
        )

        if success:
            action = (
                f"Applied {len(applied_files)} multi-file patch(es) "
                "and passed post-apply verification."
            )
            outcome = (
                "Multi-file patch application completed successfully "
                "and all resulting files passed validation."
            )
            lesson = (
                "A multi-file change should remain within the authorized "
                "plan scope and pass post-apply validation."
            )
        else:
            errors = result.get("errors") or []
            reason = "; ".join(
                str(error)
                for error in errors
                if error
            )

            action = (
                f"Multi-file patch workflow processed "
                f"{len(applied_files)} file(s) before the final "
                f"verification stage reported a failure."
            )

            outcome = (
                "Multi-file patch application failed during final "
                "verification. "
                + (
                    reason
                    if reason
                    else (
                        "The final verification stage did not accept "
                        "the resulting repository state."
                    )
                )
            )

            lesson = (
                "Treat failed multi-file changes as warnings. Recheck "
                "the current source, change plan, patch scope, and "
                "verification results before repeating the approach."
            )

        evidence = []

        if applied_files:
            evidence.append(
                f"{len(applied_files)} file(s) processed"
            )

        if result.get("stage") == "complete":
            evidence.append(
                "post-apply verification passed"
            )

        if result.get("rolled_back"):
            evidence.append(
                "rollback completed"
            )

        provenance = ExperienceProvenance(
            source="multi_file_repair",
            workflow="patch_apply",
            evidence=tuple(evidence),
            verified=success,
        )

        stored = self.recorder.record_repair(
            task=request,
            action=action,
            outcome=outcome,
            success=success,
            lesson=lesson,
            provenance=provenance,
        )

        self.link_store.save(
            ExperienceProjectLink(
                experience_id=stored.experience_id,
                project_root=str(project_root),
                file_paths=applied_files,
                symbols=target_symbols,
            )
        )

        return stored
