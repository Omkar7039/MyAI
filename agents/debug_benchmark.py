from __future__ import annotations

from dataclasses import dataclass

from agents.debug_failure_classifier import DebugFailureClassifier
from agents.debug_hypothesis import DebugHypothesisGenerator
from agents.debug_hypothesis_loop import DebugHypothesisLoop
from agents.debug_hypothesis_ranker import DebugHypothesisRanker
from agents.debug_hypothesis_verifier import DebugHypothesisVerifier
from agents.debug_investigation import DebugEvidence
from agents.debug_reinvestigator import DebugReinvestigator
from agents.debug_repair_bridge import DebugRepairBridge
from agents.debug_stop_policy import DebugStopPolicy


@dataclass(frozen=True)
class DebugBenchmarkResult:
    investigation: float
    hypothesis_generation: float
    hypothesis_ranking: float
    hypothesis_verification: float
    retry_loop: float
    classification: float
    repair_bridge: float
    reinvestigation: float
    stop_policy: float
    overall: float


class DebugBenchmark:
    def run(self) -> DebugBenchmarkResult:
        values = {
            "investigation": self._investigation(),
            "hypothesis_generation": self._hypothesis_generation(),
            "hypothesis_ranking": self._hypothesis_ranking(),
            "hypothesis_verification": self._hypothesis_verification(),
            "retry_loop": self._retry_loop(),
            "classification": self._classification(),
            "repair_bridge": self._repair_bridge(),
            "reinvestigation": self._reinvestigation(),
            "stop_policy": self._stop_policy(),
        }

        overall = sum(values.values()) / len(values)

        return DebugBenchmarkResult(
            **values,
            overall=overall,
        )

    def _evidence(self):
        return DebugEvidence(
            problem="Fix missing variable",
            language="python",
            error="NameError",
            static_analysis="undefined name detected",
            runtime={
                "language": "python",
                "success": False,
                "exit_code": 1,
                "stdout": "",
                "stderr": "NameError: missing",
                "timed_out": False,
            },
        )

    def _investigation(self):
        evidence = self._evidence()

        return 100.0 if (
            evidence.runtime_failed
            and evidence.exit_code == 1
            and evidence.stderr == "NameError: missing"
        ) else 0.0

    def _hypothesis_generation(self):
        hypotheses = DebugHypothesisGenerator().generate(
            self._evidence()
        )

        return 100.0 if (
            hypotheses
            and hypotheses[0].confidence == 95
            and hypotheses[0].evidence
        ) else 0.0

    def _hypothesis_ranking(self):
        evidence = self._evidence()
        hypotheses = DebugHypothesisGenerator().generate(evidence)
        ranked = DebugHypothesisRanker().rank(
            hypotheses,
            evidence,
        )

        return 100.0 if (
            ranked
            and ranked[0].score >= ranked[-1].score
            and ranked[0].score <= 100
        ) else 0.0

    def _hypothesis_verification(self):
        evidence = self._evidence()
        hypotheses = DebugHypothesisGenerator().generate(evidence)
        ranked = DebugHypothesisRanker().rank(
            hypotheses,
            evidence,
        )

        result = DebugHypothesisVerifier().verify(
            ranked[0].hypothesis,
            evidence,
        )

        return 100.0 if (
            result.verified
            and result.score >= 60
        ) else 0.0

    def _retry_loop(self):
        result = DebugHypothesisLoop().run(
            self._evidence()
        )

        return 100.0 if (
            result.selected is not None
            and not result.stopped_safely
            and result.attempts
        ) else 0.0

    def _classification(self):
        result = DebugFailureClassifier().classify(
            self._evidence()
        )

        return 100.0 if (
            result.category == "name"
            and result.confidence == 95
        ) else 0.0

    def _repair_bridge(self):
        evidence = self._evidence()
        hypotheses = DebugHypothesisGenerator().generate(evidence)

        request = DebugRepairBridge().build_request(
            evidence,
            hypotheses[0],
        )
        prompt = DebugRepairBridge().build_prompt(request)

        return 100.0 if (
            request.hypothesis
            and "Verified hypothesis:" in prompt
            and "Supporting evidence:" in prompt
        ) else 0.0

    def _reinvestigation(self):
        from agents.debug_investigation import DebugInvestigator

        original = self._evidence()

        final = DebugEvidence(
            problem=original.problem,
            language=original.language,
            error=original.error,
            static_analysis="clean",
            runtime={
                "language": "python",
                "success": True,
                "exit_code": 0,
                "stdout": "42",
                "stderr": "",
                "timed_out": False,
            },
        )

        class FakeInvestigator:
            def investigate(
                self,
                problem,
                code,
                error=None,
                language=None,
            ):
                return final

        result = DebugReinvestigator(
            FakeInvestigator()
        ).verify_repair(
            original,
            "missing = 42\nprint(missing)",
        )

        return 100.0 if result.resolved else 0.0

    def _stop_policy(self):
        hypothesis_result = type(
            "HypothesisResult",
            (),
            {"selected": object()},
        )()

        decision = DebugStopPolicy().decide(
            hypothesis_result=hypothesis_result,
        )

        return 100.0 if decision.action == "repair" else 0.0
