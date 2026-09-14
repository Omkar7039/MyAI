from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class ProjectSnapshot:
    project_root: str
    fingerprint: str
    total_files: int
    total_bytes: int
    symbol_count: int
    dependency_nodes: int
    dependency_edges: int
    call_nodes: int
    call_edges: int
    created_at: str


class ProjectMemoryStore:
    def __init__(self, db_path: str | Path = 'data/project_memory.db'):
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _initialize(self):
        with self._connect() as conn:
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS project_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_root TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    total_files INTEGER NOT NULL,
                    total_bytes INTEGER NOT NULL,
                    symbol_count INTEGER NOT NULL,
                    dependency_nodes INTEGER NOT NULL,
                    dependency_edges INTEGER NOT NULL,
                    call_nodes INTEGER NOT NULL,
                    call_edges INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                '''
            )
            conn.commit()

    def save(self, snapshot: ProjectSnapshot) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                '''
                INSERT INTO project_snapshots (
                    project_root, fingerprint, total_files, total_bytes,
                    symbol_count, dependency_nodes, dependency_edges,
                    call_nodes, call_edges, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    snapshot.project_root,
                    snapshot.fingerprint,
                    snapshot.total_files,
                    snapshot.total_bytes,
                    snapshot.symbol_count,
                    snapshot.dependency_nodes,
                    snapshot.dependency_edges,
                    snapshot.call_nodes,
                    snapshot.call_edges,
                    snapshot.created_at,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def latest(self, project_root: str | Path):
        with self._connect() as conn:
            row = conn.execute(
                '''
                SELECT project_root, fingerprint, total_files, total_bytes,
                       symbol_count, dependency_nodes, dependency_edges,
                       call_nodes, call_edges, created_at
                FROM project_snapshots
                WHERE project_root = ?
                ORDER BY id DESC
                LIMIT 1
                ''',
                (str(Path(project_root).expanduser().resolve()),),
            ).fetchone()

        if row is None:
            return None

        return ProjectSnapshot(*row)

    def history(self, project_root: str | Path, limit: int = 20):
        if limit < 1:
            raise ValueError('limit must be >= 1')

        with self._connect() as conn:
            rows = conn.execute(
                '''
                SELECT project_root, fingerprint, total_files, total_bytes,
                       symbol_count, dependency_nodes, dependency_edges,
                       call_nodes, call_edges, created_at
                FROM project_snapshots
                WHERE project_root = ?
                ORDER BY id DESC
                LIMIT ?
                ''',
                (str(Path(project_root).expanduser().resolve()), limit),
            ).fetchall()

        return [ProjectSnapshot(*row) for row in rows]


class ProjectSnapshotBuilder:
    @staticmethod
    def build(context, created_at: str | None = None) -> ProjectSnapshot:
        root = str(Path(context.root).expanduser().resolve())
        report = context.repository_report
        code_index = context.code_index
        dependency_graph = context.dependency_graph
        call_graph = context.call_graph

        total_files = int(getattr(report, 'total_files', len(getattr(report, 'files', []))))
        total_bytes = int(getattr(report, 'total_bytes', 0))
        symbol_count = len(getattr(code_index, 'symbols', []))
        dependency_nodes = len(getattr(dependency_graph, 'nodes', {}))
        dependency_edges = sum(
            len(getattr(node, 'imports', []))
            for node in getattr(dependency_graph, 'nodes', {}).values()
        )
        call_nodes = len(getattr(call_graph, 'nodes', {}))
        call_edges = len(getattr(call_graph, 'edges', []))

        fingerprint_data = {
            'root': root,
            'files': [],
        }

        for info in getattr(report, 'files', []):
            fingerprint_data['files'].append(
                {
                    'path': str(getattr(info, 'path', '')),
                    'size': int(getattr(info, 'size', 0)),
                    'language': str(getattr(info, 'language', '')),
                }
            )

        fingerprint_data['files'].sort(
            key=lambda item: item['path']
        )

        payload = json.dumps(
            fingerprint_data,
            sort_keys=True,
            separators=(',', ':'),
        ).encode('utf-8')

        fingerprint = hashlib.sha256(payload).hexdigest()

        timestamp = created_at or datetime.now(timezone.utc).isoformat()

        return ProjectSnapshot(
            project_root=root,
            fingerprint=fingerprint,
            total_files=total_files,
            total_bytes=total_bytes,
            symbol_count=symbol_count,
            dependency_nodes=dependency_nodes,
            dependency_edges=dependency_edges,
            call_nodes=call_nodes,
            call_edges=call_edges,
            created_at=timestamp,
        )
