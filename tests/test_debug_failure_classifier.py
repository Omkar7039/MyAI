from agents.debug_failure_classifier import DebugFailureClassifier
from agents.debug_investigation import DebugEvidence


def evidence(
    problem="Fix bug",
    static_analysis="clean",
    stderr="",
    success=False,
    exit_code=1,
    timed_out=False,
):
    return DebugEvidence(
        problem=problem,
        language="python",
        error=None,
        static_analysis=static_analysis,
        runtime={
            "language": "python",
            "success": success,
            "exit_code": exit_code,
            "stdout": "",
            "stderr": stderr,
            "timed_out": timed_out,
        },
    )


def test_classifies_syntax_failure():
    result = DebugFailureClassifier().classify(
        evidence(stderr="SyntaxError: invalid syntax")
    )

    assert result.category == "syntax"
    assert result.confidence == 98


def test_classifies_name_failure():
    result = DebugFailureClassifier().classify(
        evidence(
            static_analysis="undefined name detected",
            stderr="NameError: missing",
        )
    )

    assert result.category == "name"
    assert result.confidence == 95


def test_classifies_type_failure():
    result = DebugFailureClassifier().classify(
        evidence(stderr="TypeError: bad operand")
    )

    assert result.category == "type"
    assert result.confidence == 90


def test_classifies_test_failure():
    result = DebugFailureClassifier().classify(
        evidence(
            problem="Tests failed after the change",
            stderr="AssertionError",
        )
    )

    assert result.category == "assertion/test"
    assert result.confidence == 90


def test_classifies_timeout_before_other_categories():
    result = DebugFailureClassifier().classify(
        evidence(
            stderr="TypeError",
            timed_out=True,
            exit_code=-1,
        )
    )

    assert result.category == "timeout"
    assert result.confidence == 100


def test_classifies_environment_failure():
    result = DebugFailureClassifier().classify(
        evidence(
            stderr="ModuleNotFoundError: No module named 'x'"
        )
    )

    assert result.category == "environment/tool"
    assert result.confidence == 85


def test_classifies_semantic_failure():
    result = DebugFailureClassifier().classify(
        evidence(
            problem="The function returns the wrong result"
        )
    )

    assert result.category == "semantic"
    assert result.confidence == 80


def test_classifies_unknown_runtime_failure():
    result = DebugFailureClassifier().classify(
        evidence(stderr="unexpected failure")
    )

    assert result.category == "unknown"
    assert result.confidence == 40


def test_classifies_success_as_no_failure():
    result = DebugFailureClassifier().classify(
        evidence(
            success=True,
            exit_code=0,
        )
    )

    assert result.category == "none"
    assert result.confidence == 100


def test_classification_is_deterministic():
    item = evidence(stderr="NameError: missing")

    first = DebugFailureClassifier().classify(item)
    second = DebugFailureClassifier().classify(item)

    assert first == second
