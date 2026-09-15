from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MultiFileRegressionResult:
    verified: bool
    checked_files: tuple[str, ...]
    failed_files: tuple[str, ...]
    reason: str


class MultiFileRegressionValidator:
    def validate(self, result, expected_files=()):
        checked = tuple(
            str(path)
            for path in result.get("checked_files", expected_files)
        )

        failed = tuple(
            str(path)
            for path in result.get("failed_files", [])
        )

        if not result.get("success", False):
            return MultiFileRegressionResult(
                verified=False,
                checked_files=checked,
                failed_files=failed,
                reason="Repair result was not successful; regression verification is unavailable.",
            )

        if failed:
            return MultiFileRegressionResult(
                verified=False,
                checked_files=checked,
                failed_files=failed,
                reason="Cross-file regression validation failed.",
            )

        expected = tuple(str(path) for path in expected_files)

        if expected and set(expected) - set(checked):
            missing = sorted(set(expected) - set(checked))

            return MultiFileRegressionResult(
                verified=False,
                checked_files=checked,
                failed_files=tuple(missing),
                reason="Not all affected files were included in regression validation.",
            )

        return MultiFileRegressionResult(
            verified=True,
            checked_files=checked,
            failed_files=(),
            reason="Cross-file regression validation passed.",
        )
