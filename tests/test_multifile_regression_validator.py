from agents.multifile_regression_validator import (
    MultiFileRegressionValidator,
)


def test_successful_regression_validation_passes():
    result = MultiFileRegressionValidator().validate(
        {
            "success": True,
            "checked_files": [
                "agents/repair.py",
                "project/project_agent.py",
            ],
            "failed_files": [],
        },
        expected_files=[
            "agents/repair.py",
            "project/project_agent.py",
        ],
    )

    assert result.verified is True
    assert result.checked_files == (
        "agents/repair.py",
        "project/project_agent.py",
    )
    assert result.failed_files == ()
    assert "passed" in result.reason.lower()


def test_failed_file_is_rejected():
    result = MultiFileRegressionValidator().validate(
        {
            "success": True,
            "checked_files": [
                "agents/repair.py",
                "project/project_agent.py",
            ],
            "failed_files": [
                "project/project_agent.py",
            ],
        },
        expected_files=[
            "agents/repair.py",
            "project/project_agent.py",
        ],
    )

    assert result.verified is False
    assert result.failed_files == (
        "project/project_agent.py",
    )
    assert "failed" in result.reason.lower()


def test_missing_expected_file_is_rejected():
    result = MultiFileRegressionValidator().validate(
        {
            "success": True,
            "checked_files": [
                "agents/repair.py",
            ],
            "failed_files": [],
        },
        expected_files=[
            "agents/repair.py",
            "project/project_agent.py",
        ],
    )

    assert result.verified is False
    assert result.failed_files == (
        "project/project_agent.py",
    )


def test_unsuccessful_repair_cannot_pass_regression_validation():
    result = MultiFileRegressionValidator().validate(
        {
            "success": False,
            "checked_files": [],
            "failed_files": [],
        },
        expected_files=[],
    )

    assert result.verified is False
    assert "not successful" in result.reason.lower()


def test_expected_files_are_not_required_when_none_are_supplied():
    result = MultiFileRegressionValidator().validate(
        {
            "success": True,
            "checked_files": [
                "main.py",
            ],
            "failed_files": [],
        }
    )

    assert result.verified is True


def test_regression_validation_is_deterministic():
    attempt = {
        "success": True,
        "checked_files": [
            "a.py",
            "b.py",
        ],
        "failed_files": [],
    }

    validator = MultiFileRegressionValidator()

    assert validator.validate(
        attempt,
        expected_files=["a.py", "b.py"],
    ) == validator.validate(
        attempt,
        expected_files=["a.py", "b.py"],
    )
