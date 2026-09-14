import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Symbol:
    name: str
    kind: str
    file: str
    line: int
    end_line: int
    parent: str | None = None


@dataclass
class FileIndex:
    path: str
    language: str
    symbols: list[Symbol] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)


@dataclass
class CodeIndex:
    root: str
    files: list[FileIndex] = field(default_factory=list)
    symbols: list[Symbol] = field(default_factory=list)


class CodeIndexer:
    def index_repository(self, root: str | Path):
        root_path = Path(root).expanduser().resolve()

        if not root_path.exists():
            raise FileNotFoundError(
                f"Repository does not exist: {root_path}"
            )

        index = CodeIndex(
            root=str(root_path)
        )

        for path in root_path.rglob("*.py"):
            if self._ignored(path, root_path):
                continue

            file_index = self._index_python_file(
                path,
                root_path,
            )

            if file_index is None:
                continue

            index.files.append(file_index)
            index.symbols.extend(
                file_index.symbols
            )

        return index

    def _index_python_file(
        self,
        path: Path,
        root: Path,
    ):
        try:
            source = path.read_text(
                encoding="utf-8"
            )
        except (OSError, UnicodeDecodeError):
            return None

        try:
            tree = ast.parse(
                source,
                filename=str(path),
            )
        except SyntaxError:
            return None

        relative = str(
            path.relative_to(root)
        )

        file_index = FileIndex(
            path=relative,
            language="python",
        )

        for node in tree.body:
            self._walk_node(
                node=node,
                file_index=file_index,
                parent=None,
            )

        return file_index

    def _walk_node(
        self,
        node,
        file_index: FileIndex,
        parent: str | None,
    ):
        if isinstance(node, ast.FunctionDef):
            symbol = Symbol(
                name=node.name,
                kind="function" if parent is None else "method",
                file=file_index.path,
                line=node.lineno,
                end_line=getattr(
                    node,
                    "end_lineno",
                    node.lineno,
                ),
                parent=parent,
            )

            file_index.symbols.append(symbol)

            for child in node.body:
                self._walk_node(
                    child,
                    file_index,
                    node.name,
                )

            return

        if isinstance(node, ast.AsyncFunctionDef):
            symbol = Symbol(
                name=node.name,
                kind="async_function"
                if parent is None
                else "async_method",
                file=file_index.path,
                line=node.lineno,
                end_line=getattr(
                    node,
                    "end_lineno",
                    node.lineno,
                ),
                parent=parent,
            )

            file_index.symbols.append(symbol)

            for child in node.body:
                self._walk_node(
                    child,
                    file_index,
                    node.name,
                )

            return

        if isinstance(node, ast.ClassDef):
            symbol = Symbol(
                name=node.name,
                kind="class",
                file=file_index.path,
                line=node.lineno,
                end_line=getattr(
                    node,
                    "end_lineno",
                    node.lineno,
                ),
                parent=parent,
            )

            file_index.symbols.append(symbol)

            for child in node.body:
                self._walk_node(
                    child,
                    file_index,
                    node.name,
                )

            return

        if isinstance(node, (ast.Import, ast.ImportFrom)):
            self._record_imports(
                node,
                file_index,
            )

        for child in ast.iter_child_nodes(node):
            self._walk_node(
                child,
                file_index,
                parent,
            )

    def _record_imports(
        self,
        node,
        file_index: FileIndex,
    ):
        if isinstance(node, ast.Import):
            for alias in node.names:
                file_index.imports.append(
                    alias.name
                )

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                file_index.imports.append(
                    node.module
                )

    def _ignored(
        self,
        path: Path,
        root: Path,
    ):
        ignored = {
            ".git",
            ".venv",
            "venv",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "node_modules",
            "dist",
            "build",
        }

        try:
            parts = path.relative_to(root).parts
        except ValueError:
            return True

        return any(
            part in ignored
            for part in parts
        )

    def find_symbol(
        self,
        index: CodeIndex,
        name: str,
    ):
        return [
            symbol
            for symbol in index.symbols
            if symbol.name == name
        ]

    def summary(
        self,
        index: CodeIndex,
    ):
        class_count = sum(
            1
            for symbol in index.symbols
            if symbol.kind == "class"
        )

        function_count = sum(
            1
            for symbol in index.symbols
            if symbol.kind
            in {
                "function",
                "async_function",
            }
        )

        method_count = sum(
            1
            for symbol in index.symbols
            if symbol.kind
            in {
                "method",
                "async_method",
            }
        )

        lines = [
            f"Repository: {index.root}",
            f"Python files: {len(index.files)}",
            f"Classes: {class_count}",
            f"Functions: {function_count}",
            f"Methods: {method_count}",
            f"Symbols: {len(index.symbols)}",
            "",
            "Files:",
        ]

        for file_index in index.files:
            lines.append(
                f"  {file_index.path} "
                f"({len(file_index.symbols)} symbols)"
            )

        return "\n".join(lines)
