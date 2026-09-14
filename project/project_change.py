from __future__ import annotations

from dataclasses import dataclass

from project.project_memory import ProjectSnapshot


@dataclass(frozen=True)
class ProjectChangeReport:
    changed: bool
    fingerprint_changed: bool
    files_delta: int
    bytes_delta: int
    symbols_delta: int
    dependency_nodes_delta: int
    dependency_edges_delta: int
    call_nodes_delta: int
    call_edges_delta: int

    @property
    def summary(self) -> str:
        if not self.changed:
            return 'Project unchanged since previous snapshot.'

        changes = []

        if self.fingerprint_changed:
            changes.append('file fingerprint changed')
        if self.files_delta:
            changes.append(f'files {self._signed(self.files_delta)}')
        if self.bytes_delta:
            changes.append(f'bytes {self._signed(self.bytes_delta)}')
        if self.symbols_delta:
            changes.append(f'symbols {self._signed(self.symbols_delta)}')
        if self.dependency_nodes_delta:
            changes.append(
                f'dependency nodes {self._signed(self.dependency_nodes_delta)}'
            )
        if self.dependency_edges_delta:
            changes.append(
                f'dependency edges {self._signed(self.dependency_edges_delta)}'
            )
        if self.call_nodes_delta:
            changes.append(
                f'call nodes {self._signed(self.call_nodes_delta)}'
            )
        if self.call_edges_delta:
            changes.append(
                f'call edges {self._signed(self.call_edges_delta)}'
            )

        return 'Project changed: ' + ', '.join(changes) + '.'

    @staticmethod
    def _signed(value: int) -> str:
        return f'{value:+d}'


class ProjectChangeDetector:
    def compare(
        self,
        previous: ProjectSnapshot | None,
        current: ProjectSnapshot,
    ) -> ProjectChangeReport:
        if previous is None:
            return ProjectChangeReport(
                changed=True,
                fingerprint_changed=True,
                files_delta=current.total_files,
                bytes_delta=current.total_bytes,
                symbols_delta=current.symbol_count,
                dependency_nodes_delta=current.dependency_nodes,
                dependency_edges_delta=current.dependency_edges,
                call_nodes_delta=current.call_nodes,
                call_edges_delta=current.call_edges,
            )

        fingerprint_changed = previous.fingerprint != current.fingerprint
        files_delta = current.total_files - previous.total_files
        bytes_delta = current.total_bytes - previous.total_bytes
        symbols_delta = current.symbol_count - previous.symbol_count
        dependency_nodes_delta = current.dependency_nodes - previous.dependency_nodes
        dependency_edges_delta = current.dependency_edges - previous.dependency_edges
        call_nodes_delta = current.call_nodes - previous.call_nodes
        call_edges_delta = current.call_edges - previous.call_edges

        changed = any(
            [
                fingerprint_changed,
                files_delta,
                bytes_delta,
                symbols_delta,
                dependency_nodes_delta,
                dependency_edges_delta,
                call_nodes_delta,
                call_edges_delta,
            ]
        )

        return ProjectChangeReport(
            changed=changed,
            fingerprint_changed=fingerprint_changed,
            files_delta=files_delta,
            bytes_delta=bytes_delta,
            symbols_delta=symbols_delta,
            dependency_nodes_delta=dependency_nodes_delta,
            dependency_edges_delta=dependency_edges_delta,
            call_nodes_delta=call_nodes_delta,
            call_edges_delta=call_edges_delta,
        )
