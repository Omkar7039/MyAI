from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from project.change_aware_context import ChangeAwareContextAssembler
from project.project_agent import ProjectAgent
from project.project_history import ProjectHistoryQuery
from project.project_memory import ProjectMemoryStore
from project.project_memory_dedup import ProjectMemoryDeduplicator
from project.project_memory_health import ProjectMemoryHealthChecker
from project.project_memory_policy import AutomaticProjectMemoryUpdater
from project.project_memory_reconcile import ProjectMemoryReconciler
from project.project_state import ProjectStateManager


@dataclass(frozen=True)
class ProjectMemoryBenchmarkResult:
    snapshots: float
    change_detection: float
    file_tracking: float
    history: float
    deduplication: float
    health: float
    reconciliation: float
    automatic_update: float
    change_aware_context: float
    project_agent: float
    overall: float


class ProjectMemoryBenchmark:
    def run(self) -> ProjectMemoryBenchmarkResult:
        return ProjectMemoryBenchmarkResult(
            snapshots=self._test_snapshots(),
            change_detection=self._test_change_detection(),
            file_tracking=self._test_file_tracking(),
            history=self._test_history(),
            deduplication=self._test_deduplication(),
            health=self._test_health(),
            reconciliation=self._test_reconciliation(),
            automatic_update=self._test_automatic_update(),
            change_aware_context=self._test_change_aware_context(),
            project_agent=self._test_project_agent(),
            overall=0.0,
        )._with_overall()

    def _test_snapshots(self):
        from project.project_memory import ProjectSnapshotBuilder

        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            context = self._context(
                root,
                [("main.py", 100)],
            )
            snapshot = ProjectSnapshotBuilder.build(context)

            return 100.0 if (
                snapshot.project_root == str(root)
                and snapshot.total_files == 1
                and snapshot.file_manifest == (("main.py", 100),)
                and len(snapshot.fingerprint) == 64
            ) else 0.0

    def _test_change_detection(self):
        from project.project_change import ProjectChangeDetector
        from project.project_memory import ProjectSnapshotBuilder

        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()

            previous = ProjectSnapshotBuilder.build(
                self._context(root, [("main.py", 100)])
            )
            current = ProjectSnapshotBuilder.build(
                self._context(
                    root,
                    [("main.py", 150), ("new.py", 50)],
                )
            )

            result = ProjectChangeDetector().compare(
                previous,
                current,
            )

            return 100.0 if (
                result.changed
                and result.files_delta == 1
                and result.bytes_delta == 100
            ) else 0.0

    def _test_file_tracking(self):
        from project.project_file_changes import ProjectFileChangeDetector
        from project.project_memory import ProjectSnapshotBuilder

        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()

            previous = ProjectSnapshotBuilder.build(
                self._context(
                    root,
                    [
                        ("main.py", 100),
                        ("old.py", 50),
                    ],
                )
            )
            current = ProjectSnapshotBuilder.build(
                self._context(
                    root,
                    [
                        ("main.py", 150),
                        ("new.py", 60),
                    ],
                )
            )

            changes = ProjectFileChangeDetector().compare(
                previous,
                current,
            )

            actual = {
                (item.path, item.status)
                for item in changes
            }

            expected = {
                ("main.py", "modified"),
                ("new.py", "added"),
                ("old.py", "deleted"),
            }

            return 100.0 if actual == expected else 0.0

    def _test_history(self):
        from project.project_memory import ProjectSnapshotBuilder

        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            store = ProjectMemoryStore(
                root / "project-memory.db"
            )

            snapshots = [
                ProjectSnapshotBuilder.build(
                    self._context(root, [("main.py", 100)]),
                    created_at="2026-01-01T00:00:00+00:00",
                ),
                ProjectSnapshotBuilder.build(
                    self._context(root, [("main.py", 150)]),
                    created_at="2026-02-01T00:00:00+00:00",
                ),
            ]

            for snapshot in snapshots:
                store.save(snapshot)

            history = ProjectHistoryQuery(store).latest(
                str(root)
            )

            return 100.0 if (
                len(history) == 2
                and history[0].current.created_at
                == "2026-02-01T00:00:00+00:00"
                and history[0].previous is not None
            ) else 0.0

    def _test_deduplication(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            store = ProjectMemoryStore(
                root / "project-memory.db"
            )
            dedup = ProjectMemoryDeduplicator(store)
            context = self._context(
                root,
                [("main.py", 100)],
            )

            first = dedup.save_if_changed(context)
            second = dedup.save_if_changed(context)

            return 100.0 if (
                first.saved
                and not second.saved
                and len(store.history(root)) == 1
            ) else 0.0

    def _test_health(self):
        from project.project_memory import ProjectSnapshotBuilder

        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            store = ProjectMemoryStore(
                root / "project-memory.db"
            )

            store.save(
                ProjectSnapshotBuilder.build(
                    self._context(
                        root,
                        [("main.py", 100)],
                    )
                )
            )

            health = ProjectMemoryHealthChecker(store).check(
                str(root)
            )

            return 100.0 if (
                health.healthy
                and health.latest_available
                and health.manifests_valid
            ) else 0.0

    def _test_reconciliation(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            store = ProjectMemoryStore(
                root / "project-memory.db"
            )
            reconciler = ProjectMemoryReconciler(store)

            first = self._context(
                root,
                [("main.py", 100)],
            )
            second = self._context(
                root,
                [("main.py", 150)],
            )

            initial = reconciler.reconcile(first)
            current = reconciler.inspect(second)

            return 100.0 if (
                initial.needs_update
                and current.needs_update
                and current.stored is not None
            ) else 0.0

    def _test_automatic_update(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            store = ProjectMemoryStore(
                root / "project-memory.db"
            )
            updater = AutomaticProjectMemoryUpdater(
                ProjectMemoryReconciler(store)
            )

            context = self._context(
                root,
                [("main.py", 100)],
            )

            first = updater.update(context)
            second = updater.update(context)

            return 100.0 if (
                first[1].should_update
                and not second[1].should_update
                and len(store.history(root)) == 1
            ) else 0.0

    def _test_change_aware_context(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "repair.py").write_text(
                "def repair():\n    return 1\n",
                encoding="utf-8",
            )
            (root / "utils.py").write_text(
                "def helper():\n    return 2\n",
                encoding="utf-8",
            )

            assembler = ChangeAwareContextAssembler(
                root=root,
            ) if False else ChangeAwareContextAssembler()

            assembler.retriever.root = root

            context = assembler.assemble(
                ["repair.py", "utils.py"],
                request="helper bug",
                changed_files=["utils.py"],
            )

            return 100.0 if (
                context.files
                and context.files[0]["file"] == "utils.py"
                and len(context.text) <= 6000
            ) else 0.0

    def _test_project_agent(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            store = ProjectMemoryStore(
                root / "project-memory.db"
            )
            manager = ProjectStateManager(store)

            agent = ProjectAgent.__new__(ProjectAgent)
            agent.project_memory_store = store
            agent.project_state_manager = manager

            from project.project_state_context import (
                ProjectStateContextBuilder,
            )

            agent.project_state_context = (
                ProjectStateContextBuilder(manager)
            )

            manager.record(
                self._context(
                    root,
                    [("main.py", 100)],
                )
            )

            state = agent._collect_project_state(
                self._context(
                    root,
                    [
                        ("main.py", 150),
                        ("new.py", 50),
                    ],
                )
            )

            return 100.0 if (
                state["previous_snapshot"] is not None
                and state["current_snapshot"] is not None
                and state["changed_files"]
            ) else 0.0

    @staticmethod
    def _context(root, files):
        infos = [
            SimpleNamespace(
                path=path,
                size=size,
                language="python",
            )
            for path, size in files
        ]

        return SimpleNamespace(
            root=str(root),
            repository_report=SimpleNamespace(
                files=infos,
                total_files=len(infos),
                total_bytes=sum(
                    size for _, size in files
                ),
            ),
            code_index=SimpleNamespace(
                symbols=[]
            ),
            dependency_graph=SimpleNamespace(
                nodes={}
            ),
            call_graph=SimpleNamespace(
                nodes={},
                edges=[],
            ),
        )


def _with_overall(result):
    values = [
        result.snapshots,
        result.change_detection,
        result.file_tracking,
        result.history,
        result.deduplication,
        result.health,
        result.reconciliation,
        result.automatic_update,
        result.change_aware_context,
        result.project_agent,
    ]
    overall = sum(values) / len(values)

    return ProjectMemoryBenchmarkResult(
        snapshots=result.snapshots,
        change_detection=result.change_detection,
        file_tracking=result.file_tracking,
        history=result.history,
        deduplication=result.deduplication,
        health=result.health,
        reconciliation=result.reconciliation,
        automatic_update=result.automatic_update,
        change_aware_context=result.change_aware_context,
        project_agent=result.project_agent,
        overall=overall,
    )


ProjectMemoryBenchmarkResult._with_overall = _with_overall
