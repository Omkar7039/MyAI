from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class MemoryChunk:
    chunk_id: str
    file_path: str
    start_line: int
    end_line: int
    content: str
    kind: str = "code"


class MemoryStore:
    """
    Persistent local memory for MyAI.

    Uses SQLite only. No network access and no model inference.
    """

    def __init__(self, db_path: str | Path = "data/memory.db"):
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
                CREATE TABLE IF NOT EXISTS documents (
                    file_path TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    indexed_at TEXT NOT NULL
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    start_line INTEGER NOT NULL,
                    end_line INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    FOREIGN KEY(file_path)
                        REFERENCES documents(file_path)
                        ON DELETE CASCADE
                )
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chunks_file
                ON chunks(file_path)
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chunks_kind
                ON chunks(kind)
                """
            )

    def upsert_document(
        self,
        file_path: str,
        content_hash: str,
        size_bytes: int,
        indexed_at: str,
        chunks: Iterable[MemoryChunk],
    ) -> None:
        chunks = list(chunks)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO documents (
                    file_path,
                    content_hash,
                    size_bytes,
                    indexed_at
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    content_hash = excluded.content_hash,
                    size_bytes = excluded.size_bytes,
                    indexed_at = excluded.indexed_at
                """,
                (
                    file_path,
                    content_hash,
                    size_bytes,
                    indexed_at,
                ),
            )

            conn.execute(
                "DELETE FROM chunks WHERE file_path = ?",
                (file_path,),
            )

            conn.executemany(
                """
                INSERT INTO chunks (
                    chunk_id,
                    file_path,
                    start_line,
                    end_line,
                    content,
                    kind
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk.chunk_id,
                        chunk.file_path,
                        chunk.start_line,
                        chunk.end_line,
                        chunk.content,
                        chunk.kind,
                    )
                    for chunk in chunks
                ],
            )

    def delete_document(self, file_path: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM chunks WHERE file_path = ?",
                (file_path,),
            )
            conn.execute(
                "DELETE FROM documents WHERE file_path = ?",
                (file_path,),
            )

    def document(self, file_path: str):
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT file_path, content_hash, size_bytes, indexed_at
                FROM documents
                WHERE file_path = ?
                """,
                (file_path,),
            ).fetchone()

        return dict(row) if row else None

    def chunks_for_file(self, file_path: str) -> list[MemoryChunk]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    chunk_id,
                    file_path,
                    start_line,
                    end_line,
                    content,
                    kind
                FROM chunks
                WHERE file_path = ?
                ORDER BY start_line
                """,
                (file_path,),
            ).fetchall()

        return [
            MemoryChunk(
                chunk_id=row["chunk_id"],
                file_path=row["file_path"],
                start_line=row["start_line"],
                end_line=row["end_line"],
                content=row["content"],
                kind=row["kind"],
            )
            for row in rows
        ]

    def count_documents(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM documents"
            ).fetchone()

        return int(row["count"])

    def count_chunks(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM chunks"
            ).fetchone()

        return int(row["count"])

    def close(self) -> None:
        # Connections are short-lived and managed with context managers.
        # This method exists for API compatibility/future connection pooling.
        return None
