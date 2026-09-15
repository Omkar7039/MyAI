from agents.debug_hypothesis import DebugHypothesis
from agents.debug_investigation import DebugEvidence
from agents.debug_repair_bridge import DebugRepairBridge


def make_evidence():
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


def test_bridge_creates_bounded_repair_request():
    hypothesis = DebugHypothesis(
        description="A variable or name is referenced before it is defined.",
        evidence=(
            "runtime reports NameError",
            "static undefined-name evidence matches",
        ),
        confidence=95,
    )

    request = DebugRepairBridge().build_request(
        make_evidence(),
        hypothesis,
    )

    assert request.problem == "Fix missing variable"
    assert "defined" in request.hypothesis
    assert len(request.evidence) == 2


def test_bridge_prompt_contains_verified_hypothesis_and_evidence():
    hypothesis = DebugHypothesis(
        description="A variable or name is referenced before it is defined.",
        evidence=("runtime reports NameError",),
        confidence=95,
    )

    bridge = DebugRepairBridge()
    request = bridge.build_request(
        make_evidence(),
        hypothesis,
    )
    prompt = bridge.build_prompt(request)

    assert "Verified hypothesis:" in prompt
    assert request.hypothesis in prompt
    assert "runtime reports NameError" in prompt
    assert "smallest correct change" in prompt


def test_bridge_does_not_invent_missing_evidence():
    hypothesis = DebugHypothesis(
        description="Possible unrelated issue.",
        evidence=(),
        confidence=50,
    )

    bridge = DebugRepairBridge()
    request = bridge.build_request(
        make_evidence(),
        hypothesis,
    )
    prompt = bridge.build_prompt(request)

    assert request.evidence == ()
    assert "Supporting evidence:" in prompt
    assert "Possible unrelated issue." in prompt
