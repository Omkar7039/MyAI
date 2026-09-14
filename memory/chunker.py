from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceChunk:
    chunk_id: str
    file_path: str
    start_line: int
    end_line: int
    content: str
    kind: str
    symbol: str | None = None
    segment: int = 1


class CodeChunker:
    """
    Structure-aware source chunker.

    Python files are chunked using the AST.
    Unsupported languages use deterministic line-based chunks.
    """

    def __init__(self, max_lines: int = 80):
        if max_lines < 1:
            raise ValueError("max_lines must be >= 1")

        self.max_lines = max_lines

    def chunk(
        self,
        file_path: str,
        content: str,
        language: str | None = None,
    ) -> list[SourceChunk]:
        if not content:
            return []

        normalized = (language or "").lower()

        if normalized in {"python", "py"}:
            return self._chunk_python(file_path, content)

        return self._chunk_lines(file_path, content)

    def _chunk_python(
        self,
        file_path: str,
        content: str,
    ) -> list[SourceChunk]:
        lines = content.splitlines()

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return self._chunk_lines(file_path, content)

        chunks: list[SourceChunk] = []
        occupied: list[tuple[int, int]] = []

        def add_chunk(
            node: ast.AST,
            kind: str,
            symbol: str | None,
        ) -> None:
            start_line = getattr(node, "lineno", None)
            end_line = getattr(node, "end_lineno", None)

            if start_line is None or end_line is None:
                return

            block = lines[start_line - 1:end_line]

            if not block:
                return

            if len(block) <= self.max_lines:
                chunks.append(
                    self._make_chunk(
                        file_path=file_path,
                        start_line=start_line,
                        end_line=end_line,
                        content="\n".join(block),
                        kind=kind,
                        symbol=symbol,
                    )
                )
                occupied.append((start_line, end_line))
                return

            chunks.extend(
                self._split_large_region(
                    file_path=file_path,
                    lines=block,
                    start_line=start_line,
                    kind=kind,
                    symbol=symbol,
                )
            )
            occupied.append((start_line, end_line))

        # Top-level functions.
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                add_chunk(
                    node,
                    self._node_kind(node),
                    node.name,
                )

        # Classes and their direct methods.
        for class_node in tree.body:
            if not isinstance(class_node, ast.ClassDef):
                continue

            method_ranges: list[tuple[int, int]] = []

            for child in class_node.body:
                if isinstance(
                    child,
                    (ast.FunctionDef, ast.AsyncFunctionDef),
                ):
                    method_ranges.append(
                        (child.lineno, child.end_lineno)
                    )

                    add_chunk(
                        child,
                        self._node_kind(child),
                        f"{class_node.name}.{child.name}",
                    )

            # Class-level content only; method bodies are excluded.
            class_regions = self._subtract_ranges(
                class_node.lineno,
                class_node.end_lineno,
                method_ranges,
            )

            for start_line, end_line in class_regions:
                block = lines[start_line - 1:end_line]

                if not any(line.strip() for line in block):
                    continue

                chunks.append(
                    self._make_chunk(
                        file_path=file_path,
                        start_line=start_line,
                        end_line=end_line,
                        content="\n".join(block),
                        kind="class",
                        symbol=class_node.name,
                    )
                )
                occupied.append((start_line, end_line))

        # Module-level imports/constants/statements.
        top_level_ranges = []

        for node in tree.body:
            start_line = getattr(node, "lineno", None)
            end_line = getattr(node, "end_lineno", None)

            if start_line is not None and end_line is not None:
                top_level_ranges.append((start_line, end_line))

        module_regions = self._subtract_ranges(
            1,
            len(lines),
            top_level_ranges,
        )

        for start_line, end_line in module_regions:
            block = lines[start_line - 1:end_line]

            if not any(line.strip() for line in block):
                continue

            if len(block) <= self.max_lines:
                chunks.append(
                    self._make_chunk(
                        file_path=file_path,
                        start_line=start_line,
                        end_line=end_line,
                        content="\n".join(block),
                        kind="module",
                        symbol=None,
                    )
                )
            else:
                chunks.extend(
                    self._split_large_region(
                        file_path=file_path,
                        lines=block,
                        start_line=start_line,
                        kind="module",
                        symbol=None,
                    )
                )

        chunks.sort(
            key=lambda chunk: (
                chunk.start_line,
                chunk.end_line,
                chunk.kind,
                chunk.symbol or "",
            )
        )

        return self._deduplicate_chunks(chunks)

    @staticmethod
    def _subtract_ranges(
        start: int,
        end: int,
        excluded: list[tuple[int, int]],
    ) -> list[tuple[int, int]]:
        ranges = [(start, end)]

        for excluded_start, excluded_end in sorted(excluded):
            next_ranges = []

            for current_start, current_end in ranges:
                if (
                    excluded_end < current_start
                    or excluded_start > current_end
                ):
                    next_ranges.append(
                        (current_start, current_end)
                    )
                    continue

                if current_start < excluded_start:
                    next_ranges.append(
                        (
                            current_start,
                            excluded_start - 1,
                        )
                    )

                if excluded_end < current_end:
                    next_ranges.append(
                        (
                            excluded_end + 1,
                            current_end,
                        )
                    )

            ranges = next_ranges

        return [
            (range_start, range_end)
            for range_start, range_end in ranges
            if range_start <= range_end
        ]

    @staticmethod
    def _make_chunk(
        file_path: str,
        start_line: int,
        end_line: int,
        content: str,
        kind: str,
        symbol: str | None,
        segment: int = 1,
    ) -> SourceChunk:
        identity = (
            f"{file_path}:{start_line}:{end_line}:"
            f"{kind}:{symbol or ''}:{segment}:{content}"
        )

        chunk_id = hashlib.sha256(
            identity.encode("utf-8")
        ).hexdigest()[:24]

        return SourceChunk(
            chunk_id=chunk_id,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            content=content,
            kind=kind,
            symbol=symbol,
            segment=segment,
        )

    @staticmethod
    def _deduplicate_chunks(
        chunks: list[SourceChunk],
    ) -> list[SourceChunk]:
        seen = set()
        result = []

        for chunk in chunks:
            key = (
                chunk.file_path,
                chunk.start_line,
                chunk.end_line,
                chunk.content,
                chunk.kind,
                chunk.symbol,
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(chunk)

        return result

    def _chunk_lines(
        self,
        file_path: str,
        content: str,
    ) -> list[SourceChunk]:
        lines = content.splitlines()
        chunks: list[SourceChunk] = []

        for offset in range(0, len(lines), self.max_lines):
            block = lines[offset:offset + self.max_lines]

            if not any(line.strip() for line in block):
                continue

            start = offset + 1
            end = offset + len(block)

            chunks.append(
                self._make_chunk(
                    file_path=file_path,
                    start_line=start,
                    end_line=end,
                    content="\n".join(block),
                    kind="block",
                    symbol=None,
                )
            )

        return chunks

    def _split_large_region(
        self,
        file_path: str,
        lines: list[str],
        start_line: int,
        kind: str,
        symbol: str | None,
    ) -> list[SourceChunk]:
        chunks: list[SourceChunk] = []

        for offset in range(0, len(lines), self.max_lines):
            block = lines[offset:offset + self.max_lines]

            if not any(line.strip() for line in block):
                continue

            start = start_line + offset
            end = start + len(block) - 1

            chunks.append(
                self._make_chunk(
                    file_path=file_path,
                    start_line=start,
                    end_line=end,
                    content="\n".join(block),
                    kind=kind,
                    symbol=symbol,
                )
            )

        return chunks

    @staticmethod
    def _symbol_name(node: ast.AST) -> str | None:
        return getattr(node, "name", None)

    @staticmethod
    def _node_kind(node: ast.AST) -> str:
        if isinstance(node, ast.ClassDef):
            return "class"

        if isinstance(node, ast.AsyncFunctionDef):
            return "async_function"

        return "function"

    @staticmethod
    def _uncovered_regions(
        total_lines: int,
        occupied: list[tuple[int, int]],
    ) -> list[tuple[int, int]]:
        if total_lines == 0:
            return []

        covered = set()

        for start, end in occupied:
            covered.update(range(start, end + 1))

        regions: list[tuple[int, int]] = []
        current_start: int | None = None

        for line_number in range(1, total_lines + 1):
            if line_number not in covered:
                if current_start is None:
                    current_start = line_number
            elif current_start is not None:
                regions.append((current_start, line_number - 1))
                current_start = None

        if current_start is not None:
            regions.append((current_start, total_lines))

        return regions

    def _split_large_region(
        self,
        file_path: str,
        lines: list[str],
        start_line: int,
        kind: str,
        symbol: str | None,
    ) -> list[SourceChunk]:
        chunks: list[SourceChunk] = []

        segment = 1

        for offset in range(0, len(lines), self.max_lines):
            block = lines[offset:offset + self.max_lines]

            if not any(line.strip() for line in block):
                continue

            start = start_line + offset
            end = start + len(block) - 1

            chunks.append(
                self._make_chunk(
                    file_path=file_path,
                    start_line=start,
                    end_line=end,
                    content="\\n".join(block),
                    kind=kind,
                    symbol=symbol,
                    segment=segment,
                )
            )

            segment += 1

        return chunks
