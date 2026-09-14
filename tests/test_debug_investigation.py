from agents.debug_investigation import DebugInvestigator


class FakeAnalyzer:
    def analyze(self, code, language="unknown"):
        return f"Static analysis for {language}: clean structure."


class FakeRunner:
    def __init__(self, result=None, supported=True):
        self.result = result
        self.supported = supported

    def supports(self, language):
        return self.supported and language in {"python", "javascript"}

    def run(self, language, code):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_debug_investigator_collects_runtime_and_static_evidence():
    runtime = {
        "language": "python",
        "success": False,
        "exit_code": 1,
        "stdout": "",
        "stderr": "NameError: missing",
        "timed_out": False,
    }

    investigator = DebugInvestigator(
        analyzer=FakeAnalyzer(),
        runner_manager=FakeRunner(runtime),
    )

    evidence = investigator.investigate(
        problem="Fix missing variable",
        code="print(missing)",
        error="NameError",
        language="python",
    )

    assert evidence.problem == "Fix missing variable"
    assert evidence.language == "python"
    assert evidence.error == "NameError"
    assert evidence.runtime_available is True
    assert evidence.runtime_failed is True
    assert evidence.runtime_success is False
    assert evidence.timed_out is False
    assert evidence.exit_code == 1
    assert evidence.stderr == "NameError: missing"
    assert "Static analysis" in evidence.static_analysis


def test_debug_investigator_handles_unsupported_runtime():
    investigator = DebugInvestigator(
        analyzer=FakeAnalyzer(),
        runner_manager=FakeRunner(supported=False),
    )

    evidence = investigator.investigate(
        problem="Explain code",
        code="x = 1",
        language="ruby",
    )

    assert evidence.runtime_available is False
    assert evidence.runtime_success is False
    assert evidence.runtime_failed is False
    assert evidence.exit_code is None
    assert "Runtime execution was not available." in evidence.render()


def test_debug_investigator_normalizes_runner_exceptions():
    investigator = DebugInvestigator(
        analyzer=FakeAnalyzer(),
        runner_manager=FakeRunner(
            result=RuntimeError("runner unavailable")
        ),
    )

    evidence = investigator.investigate(
        problem="Run failing program",
        code="raise RuntimeError()",
        language="python",
    )

    assert evidence.runtime_available is True
    assert evidence.runtime_failed is True
    assert evidence.exit_code == -1
    assert "runner unavailable" in evidence.stderr
    assert evidence.timed_out is False


def test_debug_evidence_render_is_bounded():
    runtime = {
        "language": "python",
        "success": False,
        "exit_code": 1,
        "stdout": "x" * 5000,
        "stderr": "y" * 5000,
        "timed_out": False,
    }

    investigator = DebugInvestigator(
        analyzer=FakeAnalyzer(),
        runner_manager=FakeRunner(runtime),
    )

    evidence = investigator.investigate(
        problem="A" * 1000,
        code="print(1)",
        language="python",
    )

    rendered = evidence.render(max_chars=500)

    assert len(rendered) <= 500
