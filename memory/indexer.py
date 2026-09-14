from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from memory.chunker import CodeChunker
from memory.store import MemoryChunk, MemoryStore


class ProjectMemoryIndexer:
    """
    Incrementally index source files into MyAI's local memory store.

    No model inference and no network access.
    """

    DEFAULT_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".md": "markdown",
        ".txt": "text",
    }

    DEFAULT_IGNORED_DIRS = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        "logs",
    }

    def __init__(
        self,
        root: str | Path = ".",
        store: MemoryStore | None = None,
        chunker: CodeChunker | None = None,
    ):
        self.root = Path(root).expanduser().resolve()
        self.store = store or MemoryStore(
            self.root / "data" / "memory.db"
        )
        self.chunker = chunker or CodeChunker()

    def index(self, force: bool = False) -> dict:
        """
        Incrementally index the repository.

        Returns a summary containing scanned, indexed, skipped,
        deleted, and failed files.
        """
        summary = {
            "scanned": 0,
            "indexed": 0,
            "skipped": 0,
            "deleted": 0,
            "failed": [],
        }

        seen_files: set[str] = set()

        for path in self._iter_source_files():
            relative = path.relative_to(self.root).as_posix()
            seen_files.add(relative)
            summary["scanned"] += 1

            try:
                content = path.read_text(
                    encoding="utf-8",
                    errors="strict",
                )

                content_hash = self._hash(content)
                existing = self.store.document(relative)

                if (
                    not force
                    and existing
                    and existing["content_hash"] == content_hash
                ):
                    summary["skipped"] += 1
                    continue

                language = self.DEFAULT_EXTENSIONS.get(
                    path.suffix.lower(),
                    "text",
                )

                chunks = self.chunker.chunk(
                    relative,
                    content,
                    language,
                )

                memory_chunks = [
                    MemoryChunk(
                        chunk_id=chunk.chunk_id,
                        file_path=chunk.file_path,
                        start_line=chunk.start_line,
                        end_line=chunk.end_line,
                        content=chunk.content,
                        kind=(
                            f"{chunk.kind}:"
                            f"{chunk.symbol}"
                            if chunk.symbol
                            else chunk.kind
                        ),
                        segment=chunk.segment,
                    )
                    for chunk in chunks
                ]

                self.store.upsert_document(
                    file_path=relative,
                    content_hash=content_hash,
                    size_bytes=len(
                        content.encode("utf-8")
                    ),
                    indexed_at=self._now(),
                    chunks=memory_chunks,
                )

                summary["indexed"] += 1

            except Exception as exc:
                summary["failed"].append(
                    {
                        "file": relative,
                        "error": str(exc),
                    }
                )

        # Remove files that were previously indexed but no longer exist.
        existing_files = self._stored_files()

        for file_path in existing_files - seen_files:
            self.store.delete_document(file_path)
            summary["deleted"] += 1

        return summary

    def freshness(self) -> dict:
        """
        Check whether indexed memory matches the current filesystem.

        Returns stale, missing, and up-to-date files without modifying
        the memory database.
        """
        current_files = {}

        for path in self._iter_source_files():
            relative = path.relative_to(self.root).as_posix()

            try:
                content = path.read_text(
                    encoding="utf-8",
                    errors="strict",
                )
            except Exception as exc:
                current_files[relative] = {
                    "error": str(exc),
                }
                continue

            current_files[relative] = {
                "hash": self._hash(content),
            }

        indexed = {
            item["file_path"]: item
            for item in self.store.all_documents()
        }

        stale = []
        missing = []
        current = []

        for file_path, metadata in current_files.items():
            if "error" in metadata:
                stale.append(
                    {
                        "file": file_path,
                        "reason": metadata["error"],
                    }
                )
                continue

            stored = indexed.get(file_path)

            if stored is None:
                stale.append(
                    {
                        "file": file_path,
                        "reason": "not_indexed",
                    }
                )
                continue

            if stored["content_hash"] != metadata["hash"]:
                stale.append(
                    {
                        "file": file_path,
                        "reason": "content_changed",
                    }
                )
                continue

            current.append(file_path)

        for file_path in indexed:
            if file_path not in current_files:
                missing.append(file_path)

        return {
            "indexed_documents": len(indexed),
            "current_documents": len(current),
            "stale": stale,
            "missing": missing,
            "up_to_date": (
                not stale
                and not missing
                and len(current) == len(indexed)
            ),
        }

    def _iter_source_files(self):
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue

            relative_parts = path.relative_to(self.root).parts

            if any(
                part in self.DEFAULT_IGNORED_DIRS
                for part in relative_parts
            ):
                continue

            if path.name == "memory.db":
                continue

            if path.suffix.lower() not in self.DEFAULT_EXTENSIONS:
                continue

            yield path

    def _stored_files(self) -> set[str]:
        return self.store.document_paths()

    @staticmethod
    def _hash(content: str) -> str:
        return hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _now() -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()
