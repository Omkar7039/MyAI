import ast
from pathlib import Path

from project.patch_set import PatchSet


class PatchValidator:
    """
    Validate an in-memory PatchSet against the current repository.

    This class never writes files.
    """

    ALLOWED_SUFFIXES = {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".java",
        ".go",
        ".rs",
        ".cpp",
        ".cc",
        ".c",
        ".h",
        ".hpp",
        ".php",
        ".rb",
        ".sh",
        ".sql",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".md",
        ".txt",
    }

    def __init__(self, root="~/MyAI"):
        self.root = Path(root).expanduser().resolve()

    def validate(self, patch_set: PatchSet):
        errors = []
        warnings = []

        errors.extend(
            patch_set.validate()
        )

        for patch in patch_set.patches:
            errors.extend(
                self._validate_path(
                    patch.file
                )
            )

            errors.extend(
                self._validate_original(
                    patch.file,
                    patch.original,
                )
            )

            errors.extend(
                self._validate_content(
                    patch.file,
                    patch.updated,
                )
            )

            warnings.extend(
                self._validate_size(
                    patch.file,
                    patch.original,
                    patch.updated,
                )
            )

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "files_checked": len(
                patch_set.patches
            ),
        }

    def _validate_path(self, relative_path):
        errors = []

        if not relative_path:
            return ["Empty patch path."]

        candidate = (
            self.root / relative_path
        ).resolve()

        if (
            candidate != self.root
            and self.root not in candidate.parents
        ):
            errors.append(
                f"Unsafe patch path: {relative_path}"
            )
            return errors

        suffix = candidate.suffix.lower()

        if suffix and suffix not in self.ALLOWED_SUFFIXES:
            errors.append(
                f"Unsupported file type: "
                f"{relative_path}"
            )

        if candidate == self.root:
            errors.append(
                "Patch cannot target repository root."
            )

        return errors

    def _validate_original(
        self,
        relative_path,
        expected_original,
    ):
        path = self.root / relative_path

        if not path.exists():
            return [
                f"Target file does not exist: "
                f"{relative_path}"
            ]

        if not path.is_file():
            return [
                f"Patch target is not a file: "
                f"{relative_path}"
            ]

        try:
            actual = path.read_text(
                encoding="utf-8"
            )
        except (
            OSError,
            UnicodeDecodeError,
        ) as exc:
            return [
                f"Cannot read patch target "
                f"{relative_path}: {exc}"
            ]

        if actual != expected_original:
            return [
                f"Original content mismatch: "
                f"{relative_path}"
            ]

        return []

    def _validate_content(
        self,
        relative_path,
        updated,
    ):
        suffix = Path(
            relative_path
        ).suffix.lower()

        if suffix != ".py":
            return []

        try:
            ast.parse(updated)
        except SyntaxError as exc:
            return [
                f"Updated Python is invalid in "
                f"{relative_path}: {exc}"
            ]

        return []

    def _validate_size(
        self,
        relative_path,
        original,
        updated,
    ):
        old_size = len(original)
        new_size = len(updated)

        if old_size == 0:
            return [
                f"New file content detected for "
                f"{relative_path}"
            ]

        growth = new_size - old_size

        if growth > 5000:
            return [
                f"Large patch warning for "
                f"{relative_path}: "
                f"+{growth} characters"
            ]

        return []

    def validate_file_content(
        self,
        relative_path,
        content,
    ):
        """
        Validate proposed standalone content without
        comparing it with the repository.
        """
        errors = []

        errors.extend(
            self._validate_path(
                relative_path
            )
        )

        errors.extend(
            self._validate_content(
                relative_path,
                content,
            )
        )

        return {
            "valid": not errors,
            "errors": errors,
        }
