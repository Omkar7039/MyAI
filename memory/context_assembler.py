from __future__ import annotations

from dataclasses import dataclass

from memory.retriever import MemoryRetriever, RetrievedChunk


@dataclass(frozen=True)
class MemoryContext:
    query: str
    chunks: list[RetrievedChunk]
    text: str
    total_chars: int


class MemoryContextAssembler:
    """
    Build a compact, ordered memory context from retrieval results.

    Responsibilities:
      - preserve exact-symbol results
      - keep segments in source order
      - remove duplicate chunks
      - enforce a hard character budget
      - keep retrieval scores available for diagnostics
    """

    def __init__(
        self,
        retriever: MemoryRetriever | None = None,
        max_chars: int = 4000,
        max_chunks: int = 8,
    ):
        if max_chars < 1:
            raise ValueError("max_chars must be >= 1")

        if max_chunks < 1:
            raise ValueError("max_chunks must be >= 1")

        self.retriever = retriever or MemoryRetriever()
        self.max_chars = max_chars
        self.max_chunks = max_chunks

    def assemble(
        self,
        query: str,
        top_k: int = 8,
    ) -> MemoryContext:
        if not query or not query.strip():
            return MemoryContext(
                query=query,
                chunks=[],
                text="",
                total_chars=0,
            )

        limit = min(top_k, self.max_chunks)

        results = self.retriever.search(
            query,
            top_k=limit,
        )

        results = self._order_results(results)

        selected: list[RetrievedChunk] = []
        parts: list[str] = []
        total = 0

        for result in results:
            chunk = result.chunk

            header = (
                f"[{chunk.file_path}:"
                f"{chunk.start_line}-{chunk.end_line}] "
                f"{chunk.kind} "
                f"segment={chunk.segment} "
                f"score={result.score:.1f}"
            )

            block = f"{header}\n{chunk.content}\n"

            if total + len(block) > self.max_chars:
                continue

            selected.append(result)
            parts.append(block)
            total += len(block)

            if len(selected) >= self.max_chunks:
                break

        return MemoryContext(
            query=query,
            chunks=selected,
            text="\n".join(parts),
            total_chars=total,
        )

    def assemble_symbol(
        self,
        symbol: str,
        max_segments: int | None = None,
    ) -> MemoryContext:
        if not symbol or not symbol.strip():
            return MemoryContext(
                query=symbol,
                chunks=[],
                text="",
                total_chars=0,
            )

        limit = (
            max_segments
            if max_segments is not None
            else self.max_chunks
        )

        limit = min(limit, self.max_chunks)

        results = self.retriever.search_symbol_group(
            symbol,
            max_segments=limit,
        )

        return self._build_context(
            query=symbol,
            results=results,
        )

    def _build_context(
        self,
        query: str,
        results: list[RetrievedChunk],
    ) -> MemoryContext:
        selected: list[RetrievedChunk] = []
        parts: list[str] = []
        total = 0

        for result in self._order_results(results):
            chunk = result.chunk

            header = (
                f"[{chunk.file_path}:"
                f"{chunk.start_line}-{chunk.end_line}] "
                f"{chunk.kind} "
                f"segment={chunk.segment} "
                f"score={result.score:.1f}"
            )

            block = f"{header}\n{chunk.content}\n"

            if total + len(block) > self.max_chars:
                continue

            selected.append(result)
            parts.append(block)
            total += len(block)

            if len(selected) >= self.max_chunks:
                break

        return MemoryContext(
            query=query,
            chunks=selected,
            text="\n".join(parts),
            total_chars=total,
        )

    @staticmethod
    def _order_results(
        results: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        """
        Preserve useful source ordering.

        Primary ranking remains retrieval score.
        For equal/near-equal scores, source order wins.
        """
        return sorted(
            results,
            key=lambda result: (
                -result.score,
                result.chunk.file_path,
                result.chunk.start_line,
                result.chunk.segment,
            ),
        )
