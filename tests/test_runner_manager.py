from tools.runner_manager import RunnerManager


def test_runner_manager_supports_python_and_javascript():
    manager = RunnerManager()

    assert manager.supports("python") is True
    assert manager.supports("javascript") is True
    assert manager.supports("ruby") is False


def test_runner_manager_runs_python():
    manager = RunnerManager()

    result = manager.run(
        "python",
        'print("hello")',
    )

    assert result.language == "python"
    assert result.success is True
    assert result.exit_code == 0
    assert result.stdout.strip() == "hello"
    assert result.timed_out is False


def test_runner_manager_runs_javascript():
    manager = RunnerManager()

    result = manager.run(
        "javascript",
        'console.log("hello")',
    )

    assert result.language == "javascript"
    assert result.success is True
    assert result.exit_code == 0
    assert result.stdout.strip() == "hello"
    assert result.timed_out is False


def test_runner_manager_rejects_unsupported_language():
    manager = RunnerManager()

    try:
        manager.run("ruby", 'puts "hello"')
    except ValueError as exc:
        assert "No execution runner" in str(exc)
    else:
        raise AssertionError(
            "Unsupported language should raise ValueError"
        )


def test_python_runner_failure_is_normalized():
    manager = RunnerManager()

    result = manager.run(
        "python",
        "raise RuntimeError('boom')",
    )

    assert result.language == "python"
    assert result.success is False
    assert result.exit_code != 0
    assert "RuntimeError" in result.stderr
    assert result.timed_out is False
