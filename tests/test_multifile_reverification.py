from agents.multifile_reverification import MultiFileReverification


def test_successful_multifile_repair_is_verified():
    result = MultiFileReverification().verify(
        {
            "success": True,
            "stage": "complete",
            "errors": [],
            "rolled_back": False,
        }
    )

    assert result.verified is True
    assert result.rolled_back is False
    assert result.stage == "complete"
    assert result.errors == ()
    assert "passed" in result.reason.lower()


def test_failed_repair_with_rollback_is_rejected():
    result = MultiFileReverification().verify(
        {
            "success": False,
            "stage": "post_apply_verification",
            "errors": ["test failed"],
            "rolled_back": True,
        }
    )

    assert result.verified is False
    assert result.rolled_back is True
    assert result.stage == "post_apply_verification"
    assert result.errors == ("test failed",)
    assert "rolled back" in result.reason.lower()


def test_failed_repair_without_rollback_is_unverified():
    result = MultiFileReverification().verify(
        {
            "success": False,
            "stage": "validation",
            "errors": ["invalid patch"],
            "rolled_back": False,
        }
    )

    assert result.verified is False
    assert result.rolled_back is False
    assert "could not be verified" in result.reason.lower()


def test_reverification_is_deterministic():
    attempt = {
        "success": False,
        "stage": "post_apply_verification",
        "errors": ["verification failed"],
        "rolled_back": True,
    }

    verifier = MultiFileReverification()

    assert verifier.verify(attempt) == verifier.verify(attempt)
