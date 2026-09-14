from __future__ import annotations

from pathlib import Path

from dataclasses import dataclass

from experience.applicability import ExperienceApplicabilityFilter
from experience.confidence import ExperienceConfidenceCalculator
from experience.conflict import ExperienceConflictDetector
from experience.consolidator import ExperienceConsolidator
from experience.contradiction import ExperienceContradictionResolver
from experience.freshness import ExperienceFreshnessCalculator
from experience.project_link_store import ExperienceProjectLinkStore
from experience.retriever import RetrievedExperience
from experience.store import Experience, ExperienceStore


@dataclass(frozen=True)
class ExperienceScorecard:
    retrieval: float
    applicability: float
    confidence: float
    contradiction: float
    consolidation: float
    project_scoping: float
    overall: float


class ExperienceScorecardRunner:
    """Run a deterministic end-to-end experience-memory scorecard."""

    def run(self) -> ExperienceScorecard:
        retrieval = self._retrieval_score()
        applicability = self._applicability_score()
        confidence = self._confidence_score()
        contradiction = self._contradiction_score()
        consolidation = self._consolidation_score()
        project_scoping = self._project_scoping_score()

        overall = (
            retrieval
            + applicability
            + confidence
            + contradiction
            + consolidation
            + project_scoping
        ) / 6.0

        return ExperienceScorecard(
            retrieval=retrieval,
            applicability=applicability,
            confidence=confidence,
            contradiction=contradiction,
            consolidation=consolidation,
            project_scoping=project_scoping,
            overall=overall,
        )

    def _retrieval_score(self) -> float:
        with TemporaryExperienceDB() as db:
            store = ExperienceStore(db)

            strong = Experience(
                experience_id="strong",
                task="Fix parser validation bug",
                category="repair",
                action="Updated parser validation and reran regression tests.",
                outcome="Regression tests passed and mutation verification passed.",
                success=True,
                lesson="A verified parser repair should be checked against current tests.",
                metadata=(
                    '{"provenance":{"source":"repair",'
                    '"workflow":"repair_and_verify",'
                    '"evidence":["regression tests passed"],'
                    '"verified":true}}'
                ),
                created_at="2026-09-10 00:00:00",
            )

            weak = Experience(
                experience_id="weak",
                task="Fix parser validation bug",
                category="repair",
                action="Changed parser.",
                outcome="It worked.",
                success=True,
                lesson="Remember this fix.",
                created_at="2026-09-10 00:00:00",
            )

            store.add(strong)
            store.add(weak)

            results = ExperienceRetriever(store).search(
                "parser validation bug",
                limit=2,
                include_failures=True,
            )

            return 100.0 if (
                results
                and results[0].experience.experience_id == "strong"
            ) else 0.0

    def _applicability_score(self) -> float:
        experience = Experience(
            experience_id="app",
            task="Fix parser validation bug",
            category="repair",
            action="Update parser validation.",
            outcome="Tests passed.",
            success=True,
            lesson="Verify parser changes against current tests.",
        )

        result = RetrievedExperience(
            experience=experience,
            score=70.0,
        )

        applicable = ExperienceApplicabilityFilter().evaluate(
            "parser validation bug",
            result,
        )

        irrelevant = ExperienceApplicabilityFilter().evaluate(
            "database timeout deployment",
            result,
        )

        return 100.0 if (
            applicable.applicable
            and not irrelevant.applicable
        ) else 0.0

    def _confidence_score(self) -> float:
        experience = Experience(
            experience_id="confidence",
            task="Fix parser validation bug",
            category="repair",
            action="Updated parser validation and reran regression tests.",
            outcome="Regression tests passed.",
            success=True,
            lesson="Verify parser changes against current tests.",
            created_at="2026-09-10 00:00:00",
        )

        result = RetrievedExperience(
            experience=experience,
            score=70.0,
        )

        applicability = ExperienceApplicabilityFilter().evaluate(
            "parser validation bug",
            result,
        )

        freshness = ExperienceFreshnessCalculator().calculate(
            experience,
        )

        confidence = ExperienceConfidenceCalculator().calculate(
            result,
            applicability,
            freshness,
        )

        return 100.0 if confidence.label == "high" else 0.0

    def _contradiction_score(self) -> float:
        successful = RetrievedExperience(
            experience=Experience(
                experience_id="success",
                task="Fix parser validation bug",
                category="repair",
                action="Updated parser validation.",
                outcome="Regression tests passed.",
                success=True,
                lesson="Keep parser validation aligned with tests.",
            ),
            score=70.0,
        )

        failed = RetrievedExperience(
            experience=Experience(
                experience_id="failure",
                task="Fix parser validation bug",
                category="repair",
                action="Changed parser validation broadly.",
                outcome="Regression tests failed.",
                success=False,
                lesson="Require fresh verification.",
            ),
            score=40.0,
        )

        conflict = ExperienceConflictDetector().detect(
            [successful],
            [failed],
        )

        contradiction = ExperienceContradictionResolver().resolve(
            [successful],
            [failed],
        )

        return 100.0 if (
            conflict.detected
            and contradiction.detected
        ) else 0.0

    def _consolidation_score(self) -> float:
        experiences = [
            RetrievedExperience(
                experience=Experience(
                    experience_id="success",
                    task="Fix parser validation bug",
                    category="repair",
                    action="Updated parser validation.",
                    outcome="Regression tests passed.",
                    success=True,
                    lesson="Keep validation aligned with current tests.",
                ),
                score=70.0,
            ),
            RetrievedExperience(
                experience=Experience(
                    experience_id="failure",
                    task="Fix parser validation bug",
                    category="repair",
                    action="Changed parser broadly.",
                    outcome="Regression tests failed.",
                    success=False,
                    lesson="Require fresh verification.",
                ),
                score=40.0,
            ),
        ]

        result = ExperienceConsolidator().consolidate(
            experiences,
            max_chars=1200,
        )

        return 100.0 if (
            "Successful approaches:" in result.summary
            and "Warnings from failed attempts:" in result.summary
            and len(result.summary) <= 1200
        ) else 0.0

    def _project_scoping_score(self) -> float:
        with TemporaryExperienceDB() as db:
            store = ExperienceProjectLinkStore(db)

            from experience.project_link import ExperienceProjectLink

            current = ExperienceProjectLink(
                experience_id="current",
                project_root="/projects/MyAI",
                file_paths=("agents/repair.py",),
                symbols=("RepairAgent",),
            )

            other = ExperienceProjectLink(
                experience_id="other",
                project_root="/projects/Other",
                file_paths=("agents/repair.py",),
                symbols=("RepairAgent",),
            )

            store.save(current)
            store.save(other)

            project_results = store.search_project(
                "/projects/MyAI",
            )

            symbol_results = store.search_symbol(
                "RepairAgent",
            )

            return 100.0 if (
                [item.experience_id for item in project_results]
                == ["current"]
                and {
                    item.experience_id
                    for item in symbol_results
                }
                == {"current", "other"}
            ) else 0.0


class TemporaryExperienceDB:
    """Temporary SQLite path helper used by the scorecard."""

    def __enter__(self):
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        return Path(self._tmp.name) / "experience.db"

    def __exit__(self, exc_type, exc_value, traceback):
        self._tmp.cleanup()


from experience.retriever import ExperienceRetriever
