from core.orchestrator import Orchestrator


def test_orchestrator_executes_python():
    orchestrator = Orchestrator()

    result = orchestrator.execute_code(
        'print("hello from orchestrator")',
        "python",
    )

    assert result.language == "python"
    assert result.success is True
    assert result.exit_code == 0
    assert result.stdout.strip() == "hello from orchestrator"
    assert result.timed_out is False


def test_orchestrator_executes_javascript():
    orchestrator = Orchestrator()

    result = orchestrator.execute_code(
        'console.log("hello from node")',
        "javascript",
    )

    assert result.language == "javascript"
    assert result.success is True
    assert result.exit_code == 0
    assert result.stdout.strip() == "hello from node"
    assert result.timed_out is False


def test_orchestrator_rejects_unknown_language():
    orchestrator = Orchestrator()

    try:
        orchestrator.execute_code(
            'print("hello")',
            "unknown",
        )
    except ValueError as exc:
        assert "language is unknown" in str(exc)
    else:
        raise AssertionError(
            "Unknown language should be rejected"
        )


def test_orchestrator_rejects_empty_code():
    orchestrator = Orchestrator()

    try:
        orchestrator.execute_code(
            "",
            "python",
        )
    except ValueError as exc:
        assert "No code supplied" in str(exc)
    else:
        raise AssertionError(
            "Empty code should be rejected"
        )


def test_orchestrator_rejects_unsupported_language():
    orchestrator = Orchestrator()

    try:
        orchestrator.execute_code(
            'puts "hello"',
            "ruby",
        )
    except ValueError as exc:
        assert "No execution runner" in str(exc)
    else:
        raise AssertionError(
            "Unsupported language should be rejected"
        )
