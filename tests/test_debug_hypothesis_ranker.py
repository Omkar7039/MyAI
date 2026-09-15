from agents.debug_hypothesis import DebugHypothesis
from agents.debug_hypothesis_ranker import DebugHypothesisRanker
from agents.debug_investigation import DebugEvidence


def test_matching_runtime_evidence_increases_hypothesis_score():
    hypothesis = DebugHypothesis(
        description="A variable or name is referenced before it is defined.",
        evidence=("runtime reports NameError",),
        confidence=70,
    )

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
            "stderr": "NameError: missing",
            "timed_out": False,
        },
    )

    ranked = DebugHypothesisRanker().rank(
        [hypothesis],
        evidence,
    )

    assert ranked[0].score == 90
    assert "runtime/static evidence matches" in ranked[0].reasons


def test_semantic_requirement_increases_behavior_hypothesis():
    hypothesis = DebugHypothesis(
        description="The implementation does not match the intended behavior.",
        evidence=("user describes incorrect behavior",),
        confidence=70,
    )

    evidence = DebugEvidence(
        problem="The function returns the wrong result; it should return the sum.",
        language="python",
        error=None,
        static_analysis="clean",
        runtime=None,
    )

    ranked = DebugHypothesisRanker().rank(
        [hypothesis],
        evidence,
    )

    assert ranked[0].score == 90


def test_ranker_orders_strongest_hypothesis_first():
    hypotheses = [
        DebugHypothesis(
            description="Weak possibility.",
            evidence=("generic",),
            confidence=50,
        ),
        DebugHypothesis(
            description="Strong possibility.",
            evidence=("verified evidence",),
            confidence=90,
        ),
    ]

    ranked = DebugHypothesisRanker().rank(hypotheses)

    assert ranked[0].hypothesis.description == "Strong possibility."
    assert ranked[0].score == 90
    assert ranked[1].score == 50


def test_ranker_is_deterministic_and_caps_scores():
    hypothesis = DebugHypothesis(
        description="A syntax problem exists.",
        evidence=("syntax evidence",),
        confidence=100,
    )

    evidence = DebugEvidence(
        problem="Fix syntax",
        language="python",
        error="SyntaxError",
        static_analysis="syntax issue",
        runtime={
            "language": "python",
            "success": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": "SyntaxError",
            "timed_out": False,
        },
    )

    ranker = DebugHypothesisRanker()

    first = ranker.rank([hypothesis], evidence)
    second = ranker.rank([hypothesis], evidence)

    assert first == second
    assert first[0].score == 100
