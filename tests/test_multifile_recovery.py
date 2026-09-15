from agents.multifile_recovery import MultiFileRecoveryManager


def test_successful_repair_is_safe_to_continue():
    result = MultiFileRecoveryManager().evaluate(
        {
            "success": True,
            "rolled_back": False,
        }
    )

    assert result.safe_to_continue is True
    assert result.rolled_back is False
    assert "safe to continue" in result.reason.lower()


def test_failed_repair_with_rollback_is_safe():
    result = MultiFileRecoveryManager().evaluate(
        {
            "success": False,
            "rolled_back": True,
        }
    )

    assert result.safe_to_continue is True
    assert result.rolled_back is True
    assert "restored" in result.reason.lower()


def test_failed_repair_without_rollback_is_unsafe():
    result = MultiFileRecoveryManager().evaluate(
        {
            "success": False,
            "rolled_back": False,
        }
    )

    assert result.safe_to_continue is False
    assert result.rolled_back is False
    assert "recovery" in result.reason.lower()


def test_recovery_evaluation_is_deterministic():
    attempt = {
        "success": False,
        "rolled_back": True,
    }

    manager = MultiFileRecoveryManager()

    assert manager.evaluate(attempt) == manager.evaluate(attempt)
