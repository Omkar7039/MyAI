from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeFailureClassification:
    category: str
    severity: str
    retryable: bool
    recoverable: bool
    confidence: int
    reasons: tuple[str, ...]


class RuntimeFailureClassifier:
    """
    Normalize runtime failures into a small, deterministic taxonomy.

    The taxonomy intentionally overlaps with the existing debug classifier
    where appropriate, while adding runtime-specific state and lifecycle
    categories.
    """

    def classify(
        self,
        error: Exception | None = None,
        *,
        timed_out: bool = False,
        stderr: str = "",
        message: str = "",
        runtime_failed: bool = False,
    ) -> RuntimeFailureClassification:
        stderr_text = stderr.lower()
        message_text = message.lower()

        if timed_out or isinstance(error, TimeoutError):
            return RuntimeFailureClassification(
                category="timeout",
                severity="high",
                retryable=True,
                recoverable=True,
                confidence=100,
                reasons=("runtime execution timed out",),
            )

        if isinstance(error, SyntaxError) or "syntaxerror" in stderr_text:
            return RuntimeFailureClassification(
                category="syntax",
                severity="high",
                retryable=False,
                recoverable=False,
                confidence=98,
                reasons=("syntax failure detected",),
            )

        if isinstance(error, NameError) or "nameerror" in stderr_text:
            return RuntimeFailureClassification(
                category="name",
                severity="medium",
                retryable=False,
                recoverable=False,
                confidence=98,
                reasons=("undefined name failure detected",),
            )

        if isinstance(error, TypeError) or "typeerror" in stderr_text:
            return RuntimeFailureClassification(
                category="type",
                severity="medium",
                retryable=False,
                recoverable=False,
                confidence=98,
                reasons=("type failure detected",),
            )

        if (
            isinstance(error, AssertionError)
            or "assertionerror" in stderr_text
            or "test failed" in message_text
            or "tests failed" in message_text
        ):
            return RuntimeFailureClassification(
                category="assertion/test",
                severity="medium",
                retryable=True,
                recoverable=False,
                confidence=95,
                reasons=("test or assertion failure detected",),
            )

        if isinstance(
            error,
            (
                FileNotFoundError,
                ModuleNotFoundError,
                PermissionError,
                ConnectionError,
                OSError,
            ),
        ) or any(
            term in stderr_text
            for term in (
                "modulenotfounderror",
                "filenotfounderror",
                "permissionerror",
                "connectionerror",
            )
        ):
            return RuntimeFailureClassification(
                category="environment/tool",
                severity="high",
                retryable=True,
                recoverable=True,
                confidence=90,
                reasons=("environment or tool failure detected",),
            )

        if any(
            term in message_text
            for term in (
                "malformed state",
                "invalid persisted state",
                "corrupt state",
                "corrupted state",
                "invalid runtime state",
                "learning state unavailable",
                "invalid persisted runtime exit code",
            )
        ):
            return RuntimeFailureClassification(
                category="state",
                severity="high",
                retryable=False,
                recoverable=True,
                confidence=90,
                reasons=("persisted runtime state failure detected",),
            )

        if any(
            term in message_text
            for term in (
                "runtime unavailable",
                "runtime startup failed",
                "runtime shutdown failed",
                "runtime readiness failed",
            )
        ):
            return RuntimeFailureClassification(
                category="runtime",
                severity="critical",
                retryable=False,
                recoverable=True,
                confidence=90,
                reasons=("runtime lifecycle failure detected",),
            )

        if any(
            term in message_text
            for term in (
                "wrong result",
                "incorrect result",
                "wrong behavior",
                "incorrect behavior",
                "logical error",
                "logic error",
            )
        ):
            return RuntimeFailureClassification(
                category="semantic",
                severity="medium",
                retryable=True,
                recoverable=False,
                confidence=80,
                reasons=("incorrect behavior was reported",),
            )

        if runtime_failed or error is not None:
            detail = (
                str(error)
                if error is not None
                else "runtime failure was reported"
            )

            return RuntimeFailureClassification(
                category="unknown",
                severity="high",
                retryable=False,
                recoverable=False,
                confidence=40,
                reasons=(detail,),
            )

        return RuntimeFailureClassification(
            category="none",
            severity="none",
            retryable=False,
            recoverable=False,
            confidence=100,
            reasons=("no failure evidence detected",),
        )
