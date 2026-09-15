from agents.debug_hypothesis import DebugHypothesis
from agents.debug_hypothesis_verifier import DebugHypothesisVerifier
from agents.debug_investigation import DebugEvidence


def test_name_error_hypothesis_is_verified():
    hypothesis = DebugHypothesis(
        description="A variable or name is referenced before it is defined.",
        evidence=("runtime reports NameError",),
        confidence=95,
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

    result = DebugHypothesisVerifier().verify(
        hypothesis,
        evidence,
    )

    assert result.verified is True
    assert result.score == 90
    assert len(result.evidence) == 2
    assert "supported" in result.reason.lower()


def test_unsupported_hypothesis_is_rejected():
    hypothesis = DebugHypothesis(
        description="An operation is using an incompatible value type.",
        evidence=("TypeError expected",),
        confidence=90,
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

    result = DebugHypothesisVerifier().verify(
        hypothesis,
        evidence,
    )

    assert result.verified is False
    assert result.score == 0
    assert "insufficient evidence" in result.reason.lower()


def test_behavior_hypothesis_can_be_verified_from_requirement():
    hypothesis = DebugHypothesis(
        description="The implementation does not match the intended behavior.",
        evidence=("user requirement",),
        confidence=80,
    )

    evidence = DebugEvidence(
        problem="The function returns the wrong result; it should return the sum.",
        language="python",
        error=None,
        static_analysis="clean",
        runtime=None,
    )

    result = DebugHypothesisVerifier().verify(
        hypothesis,
        evidence,
    )

    assert result.verified is True
    assert result.score == 80


def test_verification_is_deterministic():
    hypothesis = DebugHypothesis(
        description="A syntax problem exists.",
        evidence=("syntax evidence",),
        confidence=98,
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

    verifier = DebugHypothesisVerifier()

    first = verifier.verify(hypothesis, evidence)
    second = verifier.verify(hypothesis, evidence)

    assert first == second
    assert first.verified is True
    assert first.score == 90
