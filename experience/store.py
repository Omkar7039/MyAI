from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Experience:
    experience_id: str
    task: str
    category: str
    action: str
    outcome: str
    success: bool
    lesson: str
    metadata: str = ""
    created_at: str = ""
    lifecycle_state: str = "active"


class ExperienceStore:
    """
    Persistent local store for MyAI's past actions and outcomes.

    Experience memory is advisory only. It is never a substitute
    for the current repository, source code, or test results.
    """

    def __init__(
        self,
        db_path: str | Path = "data/experience.db",
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
                CREATE TABLE IF NOT EXISTS experiences (
                    experience_id TEXT PRIMARY KEY,
                    task TEXT NOT NULL,
                    category TEXT NOT NULL,
                    action TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    lesson TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    lifecycle_state TEXT NOT NULL DEFAULT 'active'
                )
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_experiences_category
                ON experiences(category)
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_experiences_success
                ON experiences(success)
                """
            )

            columns = {
                row["name"]
                for row in conn.execute(
                    "PRAGMA table_info(experiences)"
                ).fetchall()
            }

            if "lifecycle_state" not in columns:
                conn.execute(
                    "ALTER TABLE experiences "
                    "ADD COLUMN lifecycle_state TEXT NOT NULL DEFAULT 'active'"
                )

    def add(self, experience: Experience) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO experiences (
                    experience_id,
                    task,
                    category,
                    action,
                    outcome,
                    success,
                    lesson,
                    metadata,
                    created_at,
                    lifecycle_state
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?,
                    COALESCE(NULLIF(?, ''), CURRENT_TIMESTAMP),
                    ?
                )
                """,
                (
                    experience.experience_id,
                    experience.task,
                    experience.category,
                    experience.action,
                    experience.outcome,
                    int(experience.success),
                    experience.lesson,
                    experience.metadata,
                    experience.created_at,
                    experience.lifecycle_state,
                ),
            )

    def get(
        self,
        experience_id: str,
    ) -> Experience | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    experience_id,
                    task,
                    category,
                    action,
                    outcome,
                    success,
                    lesson,
                    metadata,
                    created_at,
                    lifecycle_state
                FROM experiences
                WHERE experience_id = ?
                """,
                (experience_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_experience(row)

    def recent(
        self,
        limit: int = 20,
    ) -> list[Experience]:
        if limit < 1:
            raise ValueError("limit must be >= 1")

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    experience_id,
                    task,
                    category,
                    action,
                    outcome,
                    success,
                    lesson,
                    metadata,
                    created_at,
                    lifecycle_state
                FROM experiences
                WHERE lifecycle_state = 'active'
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            self._row_to_experience(row)
            for row in rows
        ]

    def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[Experience]:
        if not query or not query.strip():
            return []

        if limit < 1:
            raise ValueError("limit must be >= 1")

        pattern = f"%{query.strip()}%"

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    experience_id,
                    task,
                    category,
                    action,
                    outcome,
                    success,
                    lesson,
                    metadata,
                    created_at,
                    lifecycle_state
                FROM experiences
                WHERE lifecycle_state = 'active'
                  AND (
                    task LIKE ?
                    OR category LIKE ?
                    OR action LIKE ?
                    OR outcome LIKE ?
                    OR lesson LIKE ?
                  )
                ORDER BY
                    success DESC,
                    created_at DESC
                LIMIT ?
                """,
                (
                    pattern,
                    pattern,
                    pattern,
                    pattern,
                    pattern,
                    limit,
                ),
            ).fetchall()

        return [
            self._row_to_experience(row)
            for row in rows
        ]

    def archive(self, experience_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE experiences
                SET lifecycle_state = 'archived'
                WHERE experience_id = ?
                  AND lifecycle_state = 'active'
                """,
                (experience_id,),
            )

        return cursor.rowcount > 0

    def delete(self, experience_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM experiences WHERE experience_id = ?",
                (experience_id,),
            )

        return cursor.rowcount > 0

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM experiences"
            ).fetchone()

        return int(row["count"])

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM experiences")

    @staticmethod
    def _row_to_experience(row) -> Experience:
        return Experience(
            experience_id=row["experience_id"],
            task=row["task"],
            category=row["category"],
            action=row["action"],
            outcome=row["outcome"],
            success=bool(row["success"]),
            lesson=row["lesson"],
            metadata=row["metadata"],
            created_at=row["created_at"],
            lifecycle_state=row["lifecycle_state"],
        )
