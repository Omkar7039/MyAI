from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from core.runtime_failure import RuntimeFailureClassification
from core.runtime_recovery import RuntimeRecoveryDecision
from core.runtime_recovery_guard import RecoveryGuardResult


@dataclass(frozen=True)
class RuntimeRecoveryAuditEntry:
    entry_id: int
    created_at: str
    fingerprint: str
    category: str
    action: str
    allowed: bool
    attempts: int
    reason: str


class RuntimeRecoveryAudit:
    """
    Persistent local audit trail for runtime recovery decisions and guards.

    The audit store is independent from ExperienceStore and learning state.
    Entries are appended and never modified by this class.
    """

    SCHEMA_VERSION = 1

    def __init__(
        self,
        db_path: str | Path = "data/runtime_recovery_audit.db",
    ):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS recovery_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    category TEXT NOT NULL,
                    action TEXT NOT NULL,
                    allowed INTEGER NOT NULL,
                    attempts INTEGER NOT NULL,
                    reason TEXT NOT NULL
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS recovery_audit_metadata (
                    name TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )

            conn.execute(
                """
                INSERT OR IGNORE INTO recovery_audit_metadata(name, value)
                VALUES ('schema_version', ?)
                """,
                (str(self.SCHEMA_VERSION),),
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()

    @staticmethod
    def _validate_fingerprint(
        fingerprint: str,
    ) -> str:
        value = fingerprint.strip()

        if not value:
            raise ValueError(
                "fingerprint must not be empty"
            )

        return value

    def record(
        self,
        *,
        fingerprint: str,
        category: str,
        action: str,
        allowed: bool,
        attempts: int,
        reason: str,
    ) -> RuntimeRecoveryAuditEntry:
        fingerprint = self._validate_fingerprint(
            fingerprint
        )

        category = category.strip()
        action = action.strip()
        reason = reason.strip()

        if not category:
            raise ValueError("category must not be empty")

        if not action:
            raise ValueError("action must not be empty")

        if attempts < 0:
            raise ValueError("attempts must be >= 0")

        if not reason:
            raise ValueError("reason must not be empty")

        created_at = self._now()

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO recovery_audit(
                    created_at,
                    fingerprint,
                    category,
                    action,
                    allowed,
                    attempts,
                    reason
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    fingerprint,
                    category,
                    action,
                    int(bool(allowed)),
                    int(attempts),
                    reason,
                ),
            )

            entry_id = int(cursor.lastrowid)

        return RuntimeRecoveryAuditEntry(
            entry_id=entry_id,
            created_at=created_at,
            fingerprint=fingerprint,
            category=category,
            action=action,
            allowed=bool(allowed),
            attempts=int(attempts),
            reason=reason,
        )

    def record_decision(
        self,
        *,
        fingerprint: str,
        classification: RuntimeFailureClassification,
        decision: RuntimeRecoveryDecision,
    ) -> RuntimeRecoveryAuditEntry:
        return self.record(
            fingerprint=fingerprint,
            category=classification.category,
            action=decision.action,
            allowed=decision.safe_to_continue,
            attempts=0,
            reason=decision.reason,
        )

    def record_guard(
        self,
        *,
        fingerprint: str,
        classification: RuntimeFailureClassification,
        guard: RecoveryGuardResult,
    ) -> RuntimeRecoveryAuditEntry:
        action = "allow_recovery" if guard.allowed else "block_recovery"

        return self.record(
            fingerprint=fingerprint,
            category=classification.category,
            action=action,
            allowed=guard.allowed,
            attempts=guard.attempts,
            reason=guard.reason,
        )

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM recovery_audit"
            ).fetchone()

        return int(row[0])

    def recent(
        self,
        limit: int = 50,
    ) -> tuple[RuntimeRecoveryAuditEntry, ...]:
        if limit <= 0:
            raise ValueError("limit must be > 0")

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    created_at,
                    fingerprint,
                    category,
                    action,
                    allowed,
                    attempts,
                    reason
                FROM recovery_audit
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return tuple(
            RuntimeRecoveryAuditEntry(
                entry_id=int(row[0]),
                created_at=str(row[1]),
                fingerprint=str(row[2]),
                category=str(row[3]),
                action=str(row[4]),
                allowed=bool(row[5]),
                attempts=int(row[6]),
                reason=str(row[7]),
            )
            for row in rows
        )

    def schema_version(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT value
                FROM recovery_audit_metadata
                WHERE name = 'schema_version'
                """
            ).fetchone()

        if row is None:
            raise RuntimeError(
                "recovery audit schema version is unavailable"
            )

        return int(row[0])
