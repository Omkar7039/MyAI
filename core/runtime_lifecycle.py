from __future__ import annotations

from dataclasses import dataclass

from core.runtime_state import RuntimeStateStore


@dataclass(frozen=True)
class RuntimeStartup:
    previous_clean_shutdown: bool
    previous_status: str | None
    current_status: str


@dataclass(frozen=True)
class RuntimeShutdown:
    clean: bool
    previous_status: str | None
    current_status: str


class RuntimeLifecycle:
    """
    Manage persistent MyAI startup and graceful shutdown state.
    """

    STATUS_KEY = "runtime.status"
    CLEAN_SHUTDOWN_KEY = "runtime.clean_shutdown"
    LAST_EXIT_CODE_KEY = "runtime.last_exit_code"

    def __init__(
        self,
        store: RuntimeStateStore | None = None,
    ):
        self.store = store or RuntimeStateStore()

    def startup(self) -> RuntimeStartup:
        previous_status = self.store.value(
            self.STATUS_KEY
        )
        previous_clean = self.store.value(
            self.CLEAN_SHUTDOWN_KEY
        )

        previous_clean_shutdown = (
            previous_clean == "true"
        )

        self.store.set(
            self.STATUS_KEY,
            "starting",
        )
        self.store.set(
            self.CLEAN_SHUTDOWN_KEY,
            "false",
        )
        self.store.set(
            self.LAST_EXIT_CODE_KEY,
            "",
        )

        return RuntimeStartup(
            previous_clean_shutdown=previous_clean_shutdown,
            previous_status=previous_status,
            current_status="starting",
        )

    def mark_ready(self) -> str:
        self.store.set(
            self.STATUS_KEY,
            "ready",
        )

        return "ready"

    def shutdown(
        self,
        *,
        exit_code: int = 0,
    ) -> RuntimeShutdown:
        previous_status = self.store.value(
            self.STATUS_KEY
        )

        self.store.set(
            self.STATUS_KEY,
            "stopping",
        )
        self.store.set(
            self.LAST_EXIT_CODE_KEY,
            str(int(exit_code)),
        )

        clean = exit_code == 0

        self.store.set(
            self.CLEAN_SHUTDOWN_KEY,
            "true" if clean else "false",
        )

        self.store.set(
            self.STATUS_KEY,
            "stopped" if clean else "stopped_unclean",
        )

        return RuntimeShutdown(
            clean=clean,
            previous_status=previous_status,
            current_status=(
                "stopped"
                if clean
                else "stopped_unclean"
            ),
        )
