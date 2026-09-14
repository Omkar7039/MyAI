from __future__ import annotations

import sqlite3
from pathlib import Path

from experience.project_link import ExperienceProjectLink


class ExperienceProjectLinkStore:
    """Persistent local storage for experience-to-project links."""

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
                CREATE TABLE IF NOT EXISTS experience_project_links (
                    experience_id TEXT PRIMARY KEY,
                    project_root TEXT NOT NULL,
                    file_paths TEXT NOT NULL DEFAULT '',
                    symbols TEXT NOT NULL DEFAULT '',
                    commit_id TEXT NOT NULL DEFAULT ''
                )
                """
            )

    def save(self, link: ExperienceProjectLink) -> None:
        file_paths = "\n".join(link.file_paths)
        symbols = "\n".join(link.symbols)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO experience_project_links (
                    experience_id,
                    project_root,
                    file_paths,
                    symbols,
                    commit_id
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    link.experience_id,
                    link.project_root,
                    file_paths,
                    symbols,
                    link.commit_id,
                ),
            )

    def get(
        self,
        experience_id: str,
    ) -> ExperienceProjectLink | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    experience_id,
                    project_root,
                    file_paths,
                    symbols,
                    commit_id
                FROM experience_project_links
                WHERE experience_id = ?
                """,
                (experience_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_link(row)

    def search_project(
        self,
        project_root: str,
        limit: int = 50,
    ) -> list[ExperienceProjectLink]:
        if limit < 1:
            raise ValueError("limit must be >= 1")

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    experience_id,
                    project_root,
                    file_paths,
                    symbols,
                    commit_id
                FROM experience_project_links
                WHERE project_root = ?
                ORDER BY experience_id
                LIMIT ?
                """,
                (project_root, limit),
            ).fetchall()

        return [
            self._row_to_link(row)
            for row in rows
        ]

    def search_file(
        self,
        file_path: str,
        limit: int = 50,
    ) -> list[ExperienceProjectLink]:
        if limit < 1:
            raise ValueError("limit must be >= 1")

        pattern = "%\n" + file_path.strip() + "\n%"

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    experience_id,
                    project_root,
                    file_paths,
                    symbols,
                    commit_id
                FROM experience_project_links
                WHERE (\nfile_paths = ?
                    OR file_paths LIKE ?
                    OR file_paths LIKE ?
                    OR file_paths LIKE ?) 
                ORDER BY experience_id
                LIMIT ?
                """
                .replace("WHERE (\n", "WHERE (")
                .replace(") ", ")"),
                (
                    file_path.strip(),
                    file_path.strip() + "\n%",
                    "%\n" + file_path.strip() + "\n%",
                    "%\n" + file_path.strip(),
                    limit,
                ),
            ).fetchall()

        return [
            self._row_to_link(row)
            for row in rows
        ]

    def search_symbol(
        self,
        symbol: str,
        limit: int = 50,
    ) -> list[ExperienceProjectLink]:
        if limit < 1:
            raise ValueError("limit must be >= 1")

        symbol = symbol.strip()

        if not symbol:
            return []

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    experience_id,
                    project_root,
                    file_paths,
                    symbols,
                    commit_id
                FROM experience_project_links
                WHERE
                    symbols = ?
                    OR symbols LIKE ?
                    OR symbols LIKE ?
                    OR symbols LIKE ?
                ORDER BY experience_id
                LIMIT ?
                """,
                (
                    symbol,
                    symbol + "\n%",
                    "%\n" + symbol + "\n%",
                    "%\n" + symbol,
                    limit,
                ),
            ).fetchall()

        return [
            self._row_to_link(row)
            for row in rows
        ]

    def delete(self, experience_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM experience_project_links WHERE experience_id = ?",
                (experience_id,),
            )

        return cursor.rowcount > 0

    @staticmethod
    def _row_to_link(row) -> ExperienceProjectLink:
        file_paths = tuple(
            value
            for value in row["file_paths"].split("\n")
            if value
        )

        symbols = tuple(
            value
            for value in row["symbols"].split("\n")
            if value
        )

        return ExperienceProjectLink(
            experience_id=row["experience_id"],
            project_root=row["project_root"],
            file_paths=file_paths,
            symbols=symbols,
            commit_id=row["commit_id"],
        )
