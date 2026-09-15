from agents.debug_hypothesis import DebugHypothesis
from agents.debug_hypothesis_loop import DebugHypothesisLoop
from agents.debug_hypothesis_ranker import RankedDebugHypothesis
from agents.debug_hypothesis_verifier import HypothesisVerification
from agents.debug_investigation import DebugEvidence


class FakeGenerator:
    def __init__(self, hypotheses):
        self.hypotheses = hypotheses

    def generate(self, evidence):
        return self.hypotheses


class FakeRanker:
    def __init__(self, ranked):
        self.ranked = ranked

    def rank(self, hypotheses, evidence):
        return self.ranked


class FakeVerifier:
    def __init__(self, results):
        self.results = iter(results)

    def verify(self, hypothesis, evidence):
        return next(self.results)


def make_evidence():
    return DebugEvidence(
        problem="Fix bug",
        language="python",
        error=None,
        static_analysis="analysis",
        runtime={
            "language": "python",
            "success": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": "failure",
            "timed_out": False,
        },
    )


def test_loop_selects_first_verified_hypothesis():
    first = DebugHypothesis(
        description="First hypothesis",
        evidence=("evidence",),
        confidence=90,
    )
    second = DebugHypothesis(
        description="Second hypothesis",
        evidence=("evidence",),
        confidence=80,
    )

    ranked = [
        RankedDebugHypothesis(
            hypothesis=first,
            score=90,
            reasons=("strong",),
        ),
        RankedDebugHypothesis(
            hypothesis=second,
            score=80,
            reasons=("weaker",),
        ),
    ]

    results = [
        HypothesisVerification(
            hypothesis=first,
            verified=True,
            score=90,
            evidence=("match",),
            reason="verified",
        )
    ]

    loop = DebugHypothesisLoop(
        generator=FakeGenerator([first, second]),
        ranker=FakeRanker(ranked),
        verifier=FakeVerifier(results),
    )

    result = loop.run(make_evidence())

    assert result.selected == first
    assert len(result.attempts) == 1
    assert result.stopped_safely is False


def test_loop_retries_after_rejected_hypothesis():
    first = DebugHypothesis(
        description="Wrong hypothesis",
        evidence=("weak",),
        confidence=90,
    )
    second = DebugHypothesis(
        description="Correct hypothesis",
        evidence=("strong",),
        confidence=80,
    )

    ranked = [
        RankedDebugHypothesis(
            hypothesis=first,
            score=90,
            reasons=("first",),
        ),
        RankedDebugHypothesis(
            hypothesis=second,
            score=80,
            reasons=("second",),
        ),
    ]

    results = [
        HypothesisVerification(
            hypothesis=first,
            verified=False,
            score=20,
            evidence=(),
            reason="unsupported",
        ),
        HypothesisVerification(
            hypothesis=second,
            verified=True,
            score=80,
            evidence=("match",),
            reason="verified",
        ),
    ]

    loop = DebugHypothesisLoop(
        generator=FakeGenerator([first, second]),
        ranker=FakeRanker(ranked),
        verifier=FakeVerifier(results),
    )

    result = loop.run(make_evidence())

    assert result.selected == second
    assert len(result.attempts) == 2
    assert result.attempts[0].verified is False
    assert result.attempts[1].verified is True


def test_loop_stops_safely_when_no_hypothesis_is_verified():
    hypothesis = DebugHypothesis(
        description="Unsupported hypothesis",
        evidence=("none",),
        confidence=50,
    )

    ranked = [
        RankedDebugHypothesis(
            hypothesis=hypothesis,
            score=50,
            reasons=("weak",),
        )
    ]

    results = [
        HypothesisVerification(
            hypothesis=hypothesis,
            verified=False,
            score=0,
            evidence=(),
            reason="insufficient evidence",
        )
    ]

    loop = DebugHypothesisLoop(
        generator=FakeGenerator([hypothesis]),
        ranker=FakeRanker(ranked),
        verifier=FakeVerifier(results),
    )

    result = loop.run(make_evidence())

    assert result.selected is None
    assert len(result.attempts) == 1
    assert result.stopped_safely is True


def test_loop_is_deterministic():
    hypothesis = DebugHypothesis(
        description="Verified hypothesis",
        evidence=("evidence",),
        confidence=90,
    )

    ranked = [
        RankedDebugHypothesis(
            hypothesis=hypothesis,
            score=90,
            reasons=("strong",),
        )
    ]

    def build_loop():
        return DebugHypothesisLoop(
            generator=FakeGenerator([hypothesis]),
            ranker=FakeRanker(ranked),
            verifier=FakeVerifier(
                [
                    HypothesisVerification(
                        hypothesis=hypothesis,
                        verified=True,
                        score=90,
                        evidence=("match",),
                        reason="verified",
                    )
                ]
            ),
        )

    evidence = make_evidence()

    first = build_loop().run(evidence)
    second = build_loop().run(evidence)

    assert first == second
