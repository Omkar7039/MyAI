from pathlib import Path


class ProjectRetriever:
    def __init__(self, root="~/MyAI"):
        self.root = Path(root).expanduser().resolve()

    def read_file(self, relative_path: str):
        path = self._safe_path(relative_path)

        if not path.exists() or not path.is_file():
            return None

        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    def read_symbol(self, symbol):
        source = self.read_file(symbol.file)
        if source is None:
            return None

        lines = source.splitlines()

        start = max(symbol.line - 1, 0)
        end = min(symbol.end_line, len(lines))

        return "\n".join(lines[start:end])

    def read_symbols(self, symbols):
        """
        Retrieve the actual source for multiple symbols.

        Returns:
            list[dict]
        """
        results = []

        seen = set()

        for symbol in symbols:
            key = (
                symbol.file,
                symbol.name,
                symbol.line,
                symbol.end_line,
            )

            if key in seen:
                continue

            seen.add(key)

            source = self.read_symbol(symbol)

            if source is None:
                continue

            results.append(
                {
                    "file": symbol.file,
                    "name": symbol.name,
                    "kind": getattr(symbol, "kind", "unknown"),
                    "parent": getattr(symbol, "parent", None),
                    "line": symbol.line,
                    "end_line": symbol.end_line,
                    "source": source,
                }
            )

        return results

    def read_files(self, relative_paths):
        """
        Retrieve multiple complete source files.

        Returns:
            list[dict]
        """
        results = []
        seen = set()

        for relative_path in relative_paths:
            path_key = str(relative_path)

            if path_key in seen:
                continue

            seen.add(path_key)

            source = self.read_file(relative_path)

            if source is None:
                continue

            results.append(
                {
                    "file": path_key,
                    "source": source,
                }
            )

        return results

    def read_related_sources(self, symbols, files=None):
        """
        Retrieve symbol-level evidence and optional whole-file evidence.
        """
        symbol_evidence = self.read_symbols(symbols)

        file_evidence = []

        if files:
            file_evidence = self.read_files(files)

        return {
            "symbols": symbol_evidence,
            "files": file_evidence,
        }

    def _safe_path(self, relative_path: str):
        root = self.root.resolve()
        candidate = (root / relative_path).resolve()

        if candidate != root and root not in candidate.parents:
            raise ValueError(
                f"Unsafe project path: {relative_path}"
            )

        return candidate
