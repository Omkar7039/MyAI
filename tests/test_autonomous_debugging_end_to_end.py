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
class FakeRepairResult:
    success: bool


class FakeInvestigator:
    def __init__(self, final_evidence):
        self.final_evidence = final_evidence

    def investigate(
        self,
        problem,
        code,
        error=None,
        language=None,
    ):
        return self.final_evidence


def make_failure_evidence():
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


def make_success_evidence():
    return DebugEvidence(
        problem="Fix missing variable",
        language="python",
        error="NameError",
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


def test_full_autonomous_debugging_end_to_end():
    original = make_failure_evidence()

    classification = DebugFailureClassifier().classify(
        original
    )

    assert classification.category == "name"
    assert classification.confidence == 95

    hypotheses = DebugHypothesisGenerator().generate(
        original
    )

    assert hypotheses

    ranked = DebugHypothesisRanker().rank(
        hypotheses,
        original,
    )

    assert ranked

    verification = DebugHypothesisVerifier().verify(
        ranked[0].hypothesis,
        original,
    )

    assert verification.verified is True
    assert verification.score >= 60

    loop = DebugHypothesisLoop(
        generator=DebugHypothesisGenerator(),
        ranker=DebugHypothesisRanker(),
        verifier=DebugHypothesisVerifier(),
    )

    loop_result = loop.run(original)

    assert loop_result.selected is not None
    assert loop_result.stopped_safely is False

    repair_request = DebugRepairBridge().build_request(
        original,
        loop_result.selected,
    )

    repair_prompt = DebugRepairBridge().build_prompt(
        repair_request
    )

    assert repair_request.hypothesis
    assert "Verified hypothesis:" in repair_prompt
    assert "Supporting evidence:" in repair_prompt

    repaired_code = "missing = 42\nprint(missing)"

    reinvestigator = DebugReinvestigator(
        FakeInvestigator(
            make_success_evidence()
        )
    )

    reinvestigation = reinvestigator.verify_repair(
        original,
        repaired_code,
    )

    assert reinvestigation.resolved is True

    repair_result = FakeRepairResult(success=True)

    stop_policy = DebugStopPolicy()

    next_decision = stop_policy.decide(
        repair_result=repair_result,
        attempt_count=1,
        max_attempts=3,
    )

    assert next_decision.action == "reinvestigate"

    final_decision = stop_policy.decide(
        reinvestigation_result=reinvestigation,
        attempt_count=1,
        max_attempts=3,
    )

    assert final_decision.action == "success"
    assert "resolved" in final_decision.reason.lower()


def test_full_autonomous_debugging_stops_when_no_hypothesis_is_supported():
    evidence = DebugEvidence(
        problem="Program fails unexpectedly",
        language="python",
        error=None,
        static_analysis="no specific issue identified",
        runtime={
            "language": "python",
            "success": False,
            "exit_code": 2,
            "stdout": "",
            "stderr": "unknown failure",
            "timed_out": False,
        },
    )

    loop = DebugHypothesisLoop()
    result = loop.run(evidence)

    assert result.selected is None
    assert result.stopped_safely is True

    decision = DebugStopPolicy().decide(
        hypothesis_result=result,
        attempt_count=0,
        max_attempts=3,
    )

    assert decision.action == "stop"
    assert "No hypothesis" in decision.reason


def test_full_autonomous_debugging_respects_maximum_attempts():
    decision = DebugStopPolicy().decide(
        attempt_count=3,
        max_attempts=3,
    )

    assert decision.action == "stop"
    assert "Maximum debugging attempts" in decision.reason
