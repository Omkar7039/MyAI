from agents.debug_hypothesis import DebugHypothesisGenerator
from agents.debug_investigation import DebugEvidence


def test_name_error_generates_evidence_based_hypothesis():
    evidence = DebugEvidence(
        problem="Fix missing variable",
        language="python",
        error="NameError",
        static_analysis="undefined name detected",
        runtime={
            "language": "python",
            "success": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": "NameError: name 'missing' is not defined",
            "timed_out": False,
        },
    )

    hypotheses = DebugHypothesisGenerator().generate(evidence)

    assert hypotheses
    assert hypotheses[0].confidence == 95
    assert "defined" in hypotheses[0].description
    assert hypotheses[0].evidence


def test_semantic_problem_generates_behavior_hypothesis():
    evidence = DebugEvidence(
        problem="Function returns the wrong result; it should return the sum.",
        language="python",
        error=None,
        static_analysis="static analysis completed",
        runtime={
            "language": "python",
            "success": True,
            "exit_code": 0,
            "stdout": "5",
            "stderr": "",
            "timed_out": False,
        },
    )

    hypotheses = DebugHypothesisGenerator().generate(evidence)

    assert len(hypotheses) == 1
    assert hypotheses[0].confidence == 80
    assert "intended behavior" in hypotheses[0].description


def test_generic_runtime_failure_has_fallback_hypothesis():
    evidence = DebugEvidence(
        problem="Program fails",
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

    hypotheses = DebugHypothesisGenerator().generate(evidence)

    assert len(hypotheses) == 1
    assert hypotheses[0].confidence == 50
    assert "runtime failure" in hypotheses[0].description


def test_duplicate_hypotheses_are_removed_and_ranking_is_deterministic():
    evidence = DebugEvidence(
        problem="There is a bug and wrong result",
        language="python",
        error=None,
        static_analysis="undefined name",
        runtime={
            "language": "python",
            "success": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": "NameError: missing",
            "timed_out": False,
        },
    )

    first = DebugHypothesisGenerator().generate(evidence)
    second = DebugHypothesisGenerator().generate(evidence)

    assert first == second
    assert len(first) == 2
    assert first[0].confidence == 95
    assert first[1].confidence == 80
