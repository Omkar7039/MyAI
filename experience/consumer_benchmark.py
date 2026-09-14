from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from experience.multifile_outcome import MultiFileRepairOutcomeRecorder
from experience.project_link import ExperienceProjectLink
from experience.project_link_store import ExperienceProjectLinkStore
from experience.retriever import ExperienceRetriever
from experience.store import Experience, ExperienceStore
from project.project_agent import ProjectAgent


@dataclass(frozen=True)
class ConsumerBenchmarkResult:
    project_agent_scoping: float
    project_agent_symbol_linking: float
    multifile_success_learning: float
    multifile_failure_learning: float
    overall: float


class ConsumerBenchmark:
    def run(self) -> ConsumerBenchmarkResult:
        project_agent_scoping = self._project_agent_scoping()
        project_agent_symbol_linking = self._project_agent_symbol_linking()
        multifile_success_learning = self._multifile_outcome(success=True)
        multifile_failure_learning = self._multifile_outcome(success=False)

        overall = (
            project_agent_scoping
            + project_agent_symbol_linking
            + multifile_success_learning
            + multifile_failure_learning
        ) / 4.0

        return ConsumerBenchmarkResult(
            project_agent_scoping=project_agent_scoping,
            project_agent_symbol_linking=project_agent_symbol_linking,
            multifile_success_learning=multifile_success_learning,
            multifile_failure_learning=multifile_failure_learning,
            overall=overall,
        )

    def _project_agent_scoping(self) -> float:
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            db = root / 'experience.db'

            store = ExperienceStore(db)
            links = ExperienceProjectLinkStore(db)

            store.add(
                Experience(
                    experience_id='current',
                    task='Fix parser validation bug',
                    category='repair',
                    action='Updated parser validation.',
                    outcome='Regression tests passed.',
                    success=True,
                    lesson='Keep parser validation aligned with current tests.',
                )
            )

            store.add(
                Experience(
                    experience_id='other',
                    task='Fix parser validation bug',
                    category='repair',
                    action='Changed validation incorrectly.',
                    outcome='Regression tests failed.',
                    success=False,
                    lesson='Other project guidance.',
                )
            )

            links.save(
                ExperienceProjectLink(
                    experience_id='current',
                    project_root=str(root),
                    file_paths=('agents/repair.py',),
                    symbols=('RepairAgent',),
                )
            )

            links.save(
                ExperienceProjectLink(
                    experience_id='other',
                    project_root=str(root / 'other'),
                    file_paths=('agents/repair.py',),
                    symbols=('RepairAgent',),
                )
            )

            agent = ProjectAgent.__new__(ProjectAgent)
            agent.root = root
            agent.experience_link_store = links
            agent.experience_store = store
            agent.experience_retriever = ExperienceRetriever(store)

            result = agent._collect_project_experience(
                request='Fix parser validation bug',
                files=['agents/repair.py'],
                symbols=[],
                max_results=4,
                max_chars=1800,
            )

            ids = {
                item.experience.experience_id
                for item in result['items']
            }

            return 100.0 if (
                ids == {'current'}
                and 'current tests' in result['text']
                and 'Other project guidance.' not in result['text']
            ) else 0.0

    def _project_agent_symbol_linking(self) -> float:
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            db = root / 'experience.db'

            store = ExperienceStore(db)
            links = ExperienceProjectLinkStore(db)

            store.add(
                Experience(
                    experience_id='symbol-exp',
                    task='Fix parser validation bug',
                    category='repair',
                    action='Updated RepairAgent validation.',
                    outcome='Regression tests passed.',
                    success=True,
                    lesson='Keep RepairAgent validation aligned with current tests.',
                )
            )

            links.save(
                ExperienceProjectLink(
                    experience_id='symbol-exp',
                    project_root=str(root),
                    file_paths=('agents/repair.py',),
                    symbols=('RepairAgent',),
                )
            )

            class Symbol:
                name = 'RepairAgent'

            agent = ProjectAgent.__new__(ProjectAgent)
            agent.root = root
            agent.experience_link_store = links
            agent.experience_store = store
            agent.experience_retriever = ExperienceRetriever(store)

            result = agent._collect_project_experience(
                request='Fix parser validation bug',
                files=[],
                symbols=[Symbol()],
                max_results=4,
                max_chars=1800,
            )

            ids = {
                item.experience.experience_id
                for item in result['items']
            }

            return 100.0 if ids == {'symbol-exp'} else 0.0

    def _multifile_outcome(self, success: bool) -> float:
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            db = root / 'experience.db'

            store = ExperienceStore(db)
            links = ExperienceProjectLinkStore(db)

            class FakeRecorder:
                def record_repair(self, **kwargs):
                    experience = Experience(
                        experience_id='recorded',
                        task=kwargs['task'],
                        category='repair',
                        action=kwargs['action'],
                        outcome=kwargs['outcome'],
                        success=kwargs['success'],
                        lesson=kwargs['lesson'],
                        metadata='rollback completed' if not kwargs['success'] else '',
                    )
                    store.add(experience)
                    return experience

            class Target:
                symbol = 'RepairAgent.repair_and_verify'

            class Plan:
                targets = [Target()]

            component = MultiFileRepairOutcomeRecorder(
                recorder=FakeRecorder(),
                link_store=links,
            )

            component.record(
                request='Fix parser validation across multiple files',
                plan=Plan(),
                result={
                    'success': success,
                    'stage': 'complete' if success else 'post_apply_verification',
                    'errors': [] if success else ['Verification failed after patch application'],
                    'applied_files': ['agents/repair.py'],
                    'rolled_back': not success,
                },
                project_root=str(root),
            )

            stored = store.get('recorded')
            linked = links.get('recorded')

            if success:
                return 100.0 if (
                    stored is not None
                    and stored.success
                    and linked is not None
                    and linked.file_paths == ('agents/repair.py',)
                ) else 0.0

            return 100.0 if (
                stored is not None
                and not stored.success
                and linked is not None
                and 'rollback completed' in stored.metadata
            ) else 0.0
