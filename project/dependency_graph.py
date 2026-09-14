import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DependencyNode:
    file: str
    imports: set[str] = field(default_factory=set)
    imported_by: set[str] = field(default_factory=set)


@dataclass
class DependencyGraph:
    root: str
    nodes: dict[str, DependencyNode] = field(default_factory=dict)


class DependencyGraphBuilder:
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

        graph = DependencyGraph(
            root=str(root_path)
        )

        python_files = []

        for path in root_path.rglob("*.py"):
            if self._ignored(path, root_path):
                continue

            python_files.append(path)

            relative = str(path.relative_to(root_path))

            graph.nodes[relative] = DependencyNode(
                file=relative
            )

        module_map = self._build_module_map(
            python_files,
            root_path,
        )

        for path in python_files:
            relative = str(path.relative_to(root_path))

            imports = self._extract_imports(path)

            for imported in imports:
                target = self._resolve_local_import(
                    imported,
                    module_map,
                )

                if target and target != relative:
                    graph.nodes[relative].imports.add(target)

        for source, node in graph.nodes.items():
            for target in node.imports:
                if target in graph.nodes:
                    graph.nodes[target].imported_by.add(
                        source
                    )

        return graph

    def _build_module_map(
        self,
        files,
        root,
    ):
        module_map = {}

        for path in files:
            relative = path.relative_to(root)

            parts = list(relative.parts)

            if parts[-1] == "__init__.py":
                module_parts = parts[:-1]
            else:
                module_parts = parts[:-1] + [
                    path.stem
                ]

            if not module_parts:
                continue

            module = ".".join(module_parts)

            module_map[module] = str(relative)

        return module_map

    def _extract_imports(self, path: Path):
        try:
            source = path.read_text(
                encoding="utf-8"
            )
        except (
            OSError,
            UnicodeDecodeError,
        ):
            return set()

        try:
            tree = ast.parse(
                source,
                filename=str(path),
            )
        except SyntaxError:
            return set()

        imports = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)

        return imports

    def _resolve_local_import(
        self,
        imported,
        module_map,
    ):
        if imported in module_map:
            return module_map[imported]

        # Handle imports where only a parent module is local.
        parts = imported.split(".")

        while parts:
            candidate = ".".join(parts)

            if candidate in module_map:
                return module_map[candidate]

            parts.pop()

        return None

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

    def dependencies_of(
        self,
        graph,
        file,
    ):
        node = graph.nodes.get(file)

        if not node:
            return []

        return sorted(node.imports)

    def dependents_of(
        self,
        graph,
        file,
    ):
        node = graph.nodes.get(file)

        if not node:
            return []

        return sorted(node.imported_by)

    def summary(self, graph):
        total_edges = sum(
            len(node.imports)
            for node in graph.nodes.values()
        )

        lines = [
            f"Repository: {graph.root}",
            f"Files: {len(graph.nodes)}",
            f"Dependency edges: {total_edges}",
            "",
            "Dependencies:",
        ]

        for file in sorted(graph.nodes):
            node = graph.nodes[file]

            if not node.imports:
                continue

            lines.append(
                f"\n{file}"
            )

            for dependency in sorted(
                node.imports
            ):
                lines.append(
                    f"  -> {dependency}"
                )

        return "\n".join(lines)
