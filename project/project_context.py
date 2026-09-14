from dataclasses import dataclass, field
from pathlib import Path

from project.repository_scanner import RepositoryScanner
from project.code_index import CodeIndexer
from project.dependency_graph import DependencyGraphBuilder
from project.call_graph import CallGraphBuilder
from project.symbol_resolver import SymbolResolver


@dataclass
class ProjectContext:
    root: str
    repository_report: object
    code_index: object
    dependency_graph: object
    call_graph: object
    resolutions: list = field(default_factory=list)


class ProjectContextBuilder:
    def build(self, root: str | Path):
        root_path = Path(root).expanduser().resolve()

        scanner = RepositoryScanner()
        repository_report = scanner.scan(root_path)

        indexer = CodeIndexer()
        code_index = indexer.index_repository(root_path)

        dependency_builder = DependencyGraphBuilder()
        dependency_graph = dependency_builder.build(
            root_path
        )

        call_builder = CallGraphBuilder()
        call_graph = call_builder.build(
            root_path
        )

        resolver = SymbolResolver()
        resolver.index_repository(root_path)

        resolutions = resolver.resolve_graph(
            call_graph
        )

        return ProjectContext(
            root=str(root_path),
            repository_report=repository_report,
            code_index=code_index,
            dependency_graph=dependency_graph,
            call_graph=call_graph,
            resolutions=resolutions,
        )

    def find_symbol(
        self,
        context: ProjectContext,
        name: str,
    ):
        return [
            symbol
            for symbol in context.code_index.symbols
            if symbol.name == name
        ]

    def files_for_language(
        self,
        context: ProjectContext,
        language: str,
    ):
        return [
            info.path
            for info in context.repository_report.files
            if info.language == language
        ]

    def dependencies_of(
        self,
        context: ProjectContext,
        file: str,
    ):
        node = context.dependency_graph.nodes.get(
            file
        )

        if not node:
            return []

        return sorted(node.imports)

    def dependents_of(
        self,
        context: ProjectContext,
        file: str,
    ):
        node = context.dependency_graph.nodes.get(
            file
        )

        if not node:
            return []

        return sorted(node.imported_by)

    def calls_from(
        self,
        context: ProjectContext,
        symbol: str,
    ):
        return [
            edge
            for edge in context.call_graph.edges
            if edge.caller == symbol
        ]

    def calls_to(
        self,
        context: ProjectContext,
        symbol: str,
    ):
        return [
            edge
            for edge in context.call_graph.edges
            if edge.callee == symbol
        ]

    def resolved_calls_from(
        self,
        context: ProjectContext,
        symbol: str,
    ):
        return [
            resolution
            for resolution in context.resolutions
            if resolution.caller == symbol
        ]

    def summary(
        self,
        context: ProjectContext,
    ):
        report = context.repository_report

        lines = [
            f"Project: {context.root}",
            "",
            "Repository:",
            f"  Files: {report.total_files}",
            f"  Size: {report.total_bytes} bytes",
            "",
            "Code:",
            f"  Python files: {len(context.code_index.files)}",
            f"  Symbols: {len(context.code_index.symbols)}",
            "",
            "Dependencies:",
            f"  Files: {len(context.dependency_graph.nodes)}",
            f"  Edges: {sum(len(node.imports) for node in context.dependency_graph.nodes.values())}",
            "",
            "Calls:",
            f"  Nodes: {len(context.call_graph.nodes)}",
            f"  Edges: {len(context.call_graph.edges)}",
            "",
            "Resolved calls:",
            f"  {len(context.resolutions)}",
        ]

        return "\n".join(lines)
