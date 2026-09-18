from __future__ import annotations

from dataclasses import dataclass

from core.runtime_lifecycle import RuntimeLifecycle
from core.runtime_state import RuntimeStateStore


@dataclass(frozen=True)
class RuntimeConsistencyReport:
    consistent: bool
    issues: tuple[str, ...]


class RuntimeConsistencyChecker:
    """
    Validate logical consistency of persisted runtime lifecycle state.

    This checker is read-only. It never repairs or mutates persisted state.
    """

    VALID_STATUSES = {
        "starting",
        "ready",
        "stopping",
        "stopped",
        "stopped_unclean",
    }

    def __init__(
        self,
        store: RuntimeStateStore | None = None,
    ):
        self.store = store or RuntimeStateStore()

    def check(self) -> RuntimeConsistencyReport:
        issues: list[str] = []

        status = self.store.value(
            RuntimeLifecycle.STATUS_KEY
        )
        clean_raw = self.store.value(
            RuntimeLifecycle.CLEAN_SHUTDOWN_KEY
        )
        exit_raw = self.store.value(
            RuntimeLifecycle.LAST_EXIT_CODE_KEY
        )

        if status is None:
            if clean_raw is not None or exit_raw not in {
                None,
                "",
            }:
                issues.append(
                    "runtime metadata exists without a runtime status"
                )

            return RuntimeConsistencyReport(
                consistent=not issues,
                issues=tuple(issues),
            )

        if status not in self.VALID_STATUSES:
            issues.append(
                f"invalid runtime status: {status}"
            )

        if clean_raw not in {
            None,
            "",
            "true",
            "false",
        }:
            issues.append(
                "invalid persisted clean-shutdown value"
            )

        clean = None

        if clean_raw in {"true", "false"}:
            clean = clean_raw == "true"

        exit_code = None
        exit_present = exit_raw not in {
            None,
            "",
        }

        if exit_present:
            try:
                exit_code = int(exit_raw)
            except (TypeError, ValueError):
                issues.append(
                    "invalid persisted runtime exit code"
                )

        if status in {
            "starting",
            "ready",
            "stopping",
        }:
            if clean is True:
                issues.append(
                    f"active runtime status {status!r} "
                    "cannot have clean_shutdown=true"
                )

        if status == "stopped":
            if clean is not True:
                issues.append(
                    "stopped runtime must have clean_shutdown=true"
                )

            if exit_code is not None and exit_code != 0:
                issues.append(
                    "clean stopped runtime must have exit code 0"
                )

        if status == "stopped_unclean":
            if clean is not False:
                issues.append(
                    "unclean stopped runtime must have "
                    "clean_shutdown=false"
                )

            if exit_code == 0:
                issues.append(
                    "unclean stopped runtime must not have "
                    "exit code 0"
                )

        return RuntimeConsistencyReport(
            consistent=not issues,
            issues=tuple(issues),
        )
