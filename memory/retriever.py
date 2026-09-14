from __future__ import annotations

import re
from dataclasses import dataclass

from memory.store import MemoryChunk, MemoryStore


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: MemoryChunk
    score: float


class MemoryRetriever:
    """
    Deterministic local retrieval over indexed project chunks.

    Ranking considers:
      - exact symbol matches
      - token matches
      - file/path matches
      - query phrase matches
      - kind matches
    """

    def __init__(self, store: MemoryStore | None = None):
        self.store = store or MemoryStore("data/memory.db")

    def search(
        self,
        query: str,
        top_k: int = 8,
    ) -> list[RetrievedChunk]:
        if not query or not query.strip():
            return []

        if top_k < 1:
            raise ValueError("top_k must be >= 1")

        query = query.strip()
        query_tokens = self._tokens(query)

        results: list[RetrievedChunk] = []

        for file_path in self.store.document_paths():
            for chunk in self.store.chunks_for_file(file_path):
                score = self._score(
                    query=query,
                    query_tokens=query_tokens,
                    chunk=chunk,
                )

                if score > 0:
                    results.append(
                        RetrievedChunk(
                            chunk=chunk,
                            score=score,
                        )
                    )

        results.sort(
            key=lambda item: (
                -item.score,
                item.chunk.file_path,
                item.chunk.start_line,
                item.chunk.end_line,
            )
        )

        return self._deduplicate_context(results[:top_k])

    def search_symbol(
        self,
        symbol: str,
        top_k: int = 8,
    ) -> list[RetrievedChunk]:
        if not symbol or not symbol.strip():
            return []

        symbol = symbol.strip().lower()
        matches: list[RetrievedChunk] = []

        for file_path in self.store.document_paths():
            for chunk in self.store.chunks_for_file(file_path):
                kind = chunk.kind.lower()
                path = chunk.file_path.lower()

                if symbol in kind or symbol in path:
                    score = 100.0

                    if symbol == kind.replace("function:", ""):
                        score += 50.0

                    matches.append(
                        RetrievedChunk(
                            chunk=chunk,
                            score=score,
                        )
                    )

        matches.sort(
            key=lambda item: (
                -item.score,
                item.chunk.file_path,
                item.chunk.start_line,
            )
        )

        return matches[:top_k]

    def format_results(
        self,
        results: list[RetrievedChunk],
        max_chars: int = 12000,
    ) -> str:
        if not results:
            return ""

        parts: list[str] = []
        total = 0

        for result in results:
            chunk = result.chunk

            header = (
                f"[{chunk.file_path}:"
                f"{chunk.start_line}-{chunk.end_line}] "
                f"{chunk.kind} "
                f"(score={result.score:.1f})"
            )

            text = f"{header}\n{chunk.content}\n"

            if total + len(text) > max_chars:
                break

            parts.append(text)
            total += len(text)

        return "\n".join(parts)

    def _score(
        self,
        query: str,
        query_tokens: set[str],
        chunk: MemoryChunk,
    ) -> float:
        text = chunk.content.lower()
        file_path = chunk.file_path.lower()
        kind = chunk.kind.lower()

        score = 0.0

        normalized_query = query.lower()

        # Strongest signal: exact phrase in the chunk.
        if normalized_query in text:
            score += 40.0

        # File/path relevance.
        for token in query_tokens:
            if token in file_path:
                score += 12.0

        # Symbol/kind relevance.
        for token in query_tokens:
            if token in kind:
                score += 20.0

        # Content token overlap.
        content_tokens = self._tokens(text)

        for token in query_tokens:
            if token in content_tokens:
                score += 5.0

        # Small bonus for multiple matching query tokens.
        overlap = query_tokens.intersection(content_tokens)

        if len(overlap) >= 2:
            score += min(15.0, len(overlap) * 2.5)

        # Favor meaningful code chunks over generic blocks.
        if kind.startswith("function:"):
            score += 2.0
        elif kind.startswith("class:"):
            score += 1.0

        return score

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {
            token
            for token in re.findall(
                r"[A-Za-z_][A-Za-z0-9_.]*",
                text.lower(),
            )
            if len(token) >= 2
        }

    @staticmethod
    def _deduplicate_context(
        results: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        seen: set[str] = set()
        output: list[RetrievedChunk] = []

        for result in results:
            chunk_id = result.chunk.chunk_id

            if chunk_id in seen:
                continue

            seen.add(chunk_id)
            output.append(result)

        return output
