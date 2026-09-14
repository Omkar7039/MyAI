import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CallNode:
    symbol: str
    file: str
    line: int


@dataclass
class CallEdge:
    caller: str
    callee: str
    file: str
    line: int


@dataclass
class CallGraph:
    root: str
    nodes: dict[str, CallNode] = field(default_factory=dict)
    edges: list[CallEdge] = field(default_factory=list)


class CallGraphBuilder:
    IGNORED_DIRECTORIES = {
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

    def build(self, root: str | Path):
        root_path = Path(root).expanduser().resolve()

        if not root_path.exists():
            raise FileNotFoundError(
                f"Repository does not exist: {root_path}"
            )

        graph = CallGraph(
            root=str(root_path)
        )

        files = list(
            root_path.rglob("*.py")
        )

        for path in files:
            if self._ignored(path, root_path):
                continue

            self._index_file(
                path,
                root_path,
                graph,
            )

        return graph

    def _index_file(
        self,
        path: Path,
        root: Path,
        graph: CallGraph,
    ):
        try:
            source = path.read_text(
                encoding="utf-8"
            )
        except (
            OSError,
            UnicodeDecodeError,
        ):
            return

        try:
            tree = ast.parse(
                source,
                filename=str(path),
            )
        except SyntaxError:
            return

        relative = str(
            path.relative_to(root)
        )

        visitor = _CallVisitor(
            relative,
            graph,
        )

        visitor.visit(tree)

    def _ignored(
        self,
        path,
        root,
    ):
        try:
            parts = path.relative_to(root).parts
        except ValueError:
            return True

        return any(
            part in self.IGNORED_DIRECTORIES
            for part in parts
        )

    def callers_of(
        self,
        graph: CallGraph,
        symbol: str,
    ):
        return sorted(
            edge.caller
            for edge in graph.edges
            if edge.callee == symbol
        )

    def callees_of(
        self,
        graph: CallGraph,
        symbol: str,
    ):
        return sorted(
            edge.callee
            for edge in graph.edges
            if edge.caller == symbol
        )

    def summary(
        self,
        graph: CallGraph,
    ):
        lines = [
            f"Repository: {graph.root}",
            f"Call nodes: {len(graph.nodes)}",
            f"Call edges: {len(graph.edges)}",
            "",
            "Calls:",
        ]

        for edge in graph.edges:
            lines.append(
                f"  {edge.caller} -> {edge.callee} "
                f"({edge.file}:{edge.line})"
            )

        return "\n".join(lines)


class _CallVisitor(ast.NodeVisitor):
    def __init__(
        self,
        file_path,
        graph,
    ):
        self.file_path = file_path
        self.graph = graph
        self.scope_stack = []

    def visit_FunctionDef(self, node):
        symbol = self._symbol_name(
            node.name
        )

        self.graph.nodes[symbol] = CallNode(
            symbol=symbol,
            file=self.file_path,
            line=node.lineno,
        )

        self.scope_stack.append(
            node.name
        )

        self.generic_visit(node)

        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node):
        symbol = self._symbol_name(
            node.name
        )

        self.graph.nodes[symbol] = CallNode(
            symbol=symbol,
            file=self.file_path,
            line=node.lineno,
        )

        self.scope_stack.append(
            node.name
        )

        self.generic_visit(node)

        self.scope_stack.pop()

    def visit_ClassDef(self, node):
        self.scope_stack.append(
            node.name
        )

        self.generic_visit(node)

        self.scope_stack.pop()

    def visit_Call(self, node):
        callee = self._get_call_name(
            node.func
        )

        if callee:
            caller = self._current_caller()

            if caller:
                self.graph.edges.append(
                    CallEdge(
                        caller=caller,
                        callee=callee,
                        file=self.file_path,
                        line=node.lineno,
                    )
                )

        self.generic_visit(node)

    def _current_caller(self):
        if not self.scope_stack:
            return None

        return (
            f"{self.file_path}:"
            f"{'.'.join(self.scope_stack)}"
        )

    def _symbol_name(self, name):
        return (
            f"{self.file_path}:"
            f"{'.'.join(self.scope_stack + [name])}"
        )

    def _get_call_name(self, node):
        if isinstance(node, ast.Name):
            return node.id

        if isinstance(node, ast.Attribute):
            parts = []

            current = node

            while isinstance(
                current,
                ast.Attribute,
            ):
                parts.append(
                    current.attr
                )
                current = current.value

            if isinstance(
                current,
                ast.Name,
            ):
                parts.append(
                    current.id
                )

            return ".".join(
                reversed(parts)
            )

        return None
