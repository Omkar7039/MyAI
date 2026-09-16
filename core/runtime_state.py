from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeState:
    key: str
    value: str
    updated_at: str


class RuntimeStateStore:
    """
    Persistent local state for MyAI runtime metadata.

    This store is intentionally separate from:
      - experience memory
      - code memory
      - project snapshots

    Values are stored as strings so callers control serialization.
    """

    SCHEMA_VERSION = 1

    def __init__(
        self,
        db_path: str | Path = "data/runtime_state.db",
    ):
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_metadata (
                    name TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )

            existing = conn.execute(
                """
                SELECT value
                FROM runtime_metadata
                WHERE name = 'schema_version'
                """
            ).fetchone()

            if existing is None:
                conn.execute(
                    """
                    INSERT INTO runtime_metadata(name, value)
                    VALUES('schema_version', ?)
                    """,
                    (str(self.SCHEMA_VERSION),),
                )
            elif int(existing["value"]) != self.SCHEMA_VERSION:
                raise RuntimeError(
                    "unsupported runtime state schema version: "
                    f"{existing['value']}"
                )

    def set(
        self,
        key: str,
        value: str,
    ) -> RuntimeState:
        name = key.strip()

        if not name:
            raise ValueError("key must not be empty")

        serialized = str(value)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO runtime_state(
                    key,
                    value,
                    updated_at
                )
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (name, serialized),
            )

            row = conn.execute(
                """
                SELECT key, value, updated_at
                FROM runtime_state
                WHERE key = ?
                """,
                (name,),
            ).fetchone()

        return RuntimeState(
            key=row["key"],
            value=row["value"],
            updated_at=row["updated_at"],
        )

    def get(
        self,
        key: str,
    ) -> RuntimeState | None:
        name = key.strip()

        if not name:
            raise ValueError("key must not be empty")

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT key, value, updated_at
                FROM runtime_state
                WHERE key = ?
                """,
                (name,),
            ).fetchone()

        if row is None:
            return None

        return RuntimeState(
            key=row["key"],
            value=row["value"],
            updated_at=row["updated_at"],
        )

    def value(
        self,
        key: str,
        default: str | None = None,
    ) -> str | None:
        state = self.get(key)

        if state is None:
            return default

        return state.value

    def delete(
        self,
        key: str,
    ) -> bool:
        name = key.strip()

        if not name:
            raise ValueError("key must not be empty")

        with self._connect() as conn:
            cursor = conn.execute(
                """
                DELETE FROM runtime_state
                WHERE key = ?
                """,
                (name,),
            )

        return cursor.rowcount > 0

    def all(self) -> tuple[RuntimeState, ...]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT key, value, updated_at
                FROM runtime_state
                ORDER BY key
                """
            ).fetchall()

        return tuple(
            RuntimeState(
                key=row["key"],
                value=row["value"],
                updated_at=row["updated_at"],
            )
            for row in rows
        )

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM runtime_state")

    def schema_version(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT value
                FROM runtime_metadata
                WHERE name = 'schema_version'
                """
            ).fetchone()

        if row is None:
            return self.SCHEMA_VERSION

        return int(row["value"])
