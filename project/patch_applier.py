from pathlib import Path

from project.patch_set import PatchSet
from project.patch_validator import PatchValidator


class PatchApplier:
    """
    Safely apply a validated PatchSet.

    The operation is all-or-nothing:
      - validate before writing
      - save original contents
      - apply every patch
      - verify every resulting file
      - rollback all changes if any step fails
    """

    def __init__(self, root="~/MyAI"):
        self.root = Path(root).expanduser().resolve()
        self.validator = PatchValidator(self.root)

    def apply(self, patch_set: PatchSet):
        validation = self.validator.validate(
            patch_set
        )

        if not validation["valid"]:
            return {
                "success": False,
                "stage": "validation",
                "errors": validation["errors"],
                "warnings": validation["warnings"],
                "applied_files": [],
                "rolled_back": False,
            }

        originals = {}
        applied = []

        try:
            # Capture exact originals before touching disk.
            for patch in patch_set.patches:
                path = self._safe_path(patch.file)

                originals[patch.file] = path.read_text(
                    encoding="utf-8"
                )

            # Apply all changes.
            for patch in patch_set.patches:
                path = self._safe_path(patch.file)

                path.write_text(
                    patch.updated,
                    encoding="utf-8",
                )

                applied.append(patch.file)

            # Verify final state.
            verification_errors = self._verify_applied(
                patch_set
            )

            if verification_errors:
                self._rollback(originals)

                return {
                    "success": False,
                    "stage": "post_apply_verification",
                    "errors": verification_errors,
                    "warnings": validation["warnings"],
                    "applied_files": applied,
                    "rolled_back": True,
                }

            return {
                "success": True,
                "stage": "complete",
                "errors": [],
                "warnings": validation["warnings"],
                "applied_files": applied,
                "rolled_back": False,
            }

        except Exception as exc:
            rollback_error = None

            try:
                self._rollback(originals)
            except Exception as rollback_exc:
                rollback_error = str(rollback_exc)

            errors = [
                f"Patch application failed: {exc}"
            ]

            if rollback_error:
                errors.append(
                    f"Rollback failed: {rollback_error}"
                )

            return {
                "success": False,
                "stage": "application",
                "errors": errors,
                "warnings": validation["warnings"],
                "applied_files": applied,
                "rolled_back": rollback_error is None,
            }

    def _verify_applied(self, patch_set: PatchSet):
        errors = []

        for patch in patch_set.patches:
            path = self._safe_path(patch.file)

            try:
                actual = path.read_text(
                    encoding="utf-8"
                )
            except (
                OSError,
                UnicodeDecodeError,
            ) as exc:
                errors.append(
                    f"Cannot read {patch.file} after patch: "
                    f"{exc}"
                )
                continue

            if actual != patch.updated:
                errors.append(
                    f"Post-apply content mismatch: "
                    f"{patch.file}"
                )

            content_result = (
                self.validator.validate_file_content(
                    patch.file,
                    actual,
                )
            )

            if not content_result["valid"]:
                errors.extend(
                    content_result["errors"]
                )

        return errors

    def _rollback(self, originals):
        for relative_path, content in originals.items():
            path = self._safe_path(relative_path)

            path.write_text(
                content,
                encoding="utf-8",
            )

    def _safe_path(self, relative_path):
        candidate = (
            self.root / relative_path
        ).resolve()

        if (
            candidate != self.root
            and self.root not in candidate.parents
        ):
            raise ValueError(
                f"Unsafe patch path: {relative_path}"
            )

        if candidate == self.root:
            raise ValueError(
                "Cannot patch repository root."
            )

        return candidate
