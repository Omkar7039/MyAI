from verification.mutation_gap import MutationGapAssessment
from verification.post_repair_loop import PostRepairVerificationLoop
from verification.strategy_selector import (
    VerificationStrategy,
    VerificationStrategyDecision,
)


def decision(strategy):
    return VerificationStrategyDecision(
        strategy=strategy,
        priority=50,
        reasons=(),
    )


def mutation_result(survived):
    total = 4
    killed = total - survived

    return MutationGapAssessment(
        total_mutations=total,
        killed_mutations=killed,
        survived_mutations=survived,
        invalid_mutations=0,
        kill_rate=(killed / total) * 100.0,
        gap_rate=(survived / total) * 100.0,
        strong=survived == 0,
        reasons=(),
    )


def test_standard_strategy_passes_immediately():
    result = PostRepairVerificationLoop().verify(
        strategy=decision(VerificationStrategy.STANDARD),
        run_standard=lambda: True,
    )

    assert result.passed is True
    assert result.attempts == 1
    assert result.strategy == VerificationStrategy.STANDARD


def test_standard_strategy_stops_after_max_attempts():
    result = PostRepairVerificationLoop(max_attempts=2).verify(
        strategy=decision(VerificationStrategy.STANDARD),
        run_standard=lambda: False,
    )

    assert result.passed is False
    assert result.attempts == 2


def test_strengthening_then_standard_passes():
    calls = []

    def strengthen():
        calls.append("strengthen")
        return True

    def standard():
        calls.append("standard")
        return True

    result = PostRepairVerificationLoop().verify(
        strategy=decision(VerificationStrategy.STRENGTHEN),
        run_standard=standard,
        strengthen=strengthen,
    )

    assert result.passed is True
    assert result.strengthened is True
    assert calls == ["strengthen", "standard"]


def test_missing_strengthener_fails_safely():
    result = PostRepairVerificationLoop().verify(
        strategy=decision(VerificationStrategy.STRENGTHEN),
        run_standard=lambda: True,
    )

    assert result.passed is False
    assert "no strengthener" in result.reasons[0]


def test_mutation_strategy_passes_when_all_mutations_are_killed():
    result = PostRepairVerificationLoop().verify(
        strategy=decision(VerificationStrategy.MUTATION),
        run_standard=lambda: True,
        run_mutation=lambda: mutation_result(0),
    )

    assert result.passed is True
    assert result.mutation_gap == 0


def test_mutation_strategy_retries_when_gap_remains():
    calls = []

    def mutation():
        calls.append("mutation")
        return mutation_result(1)

    result = PostRepairVerificationLoop(max_attempts=2).verify(
        strategy=decision(VerificationStrategy.MUTATION),
        run_standard=lambda: True,
        run_mutation=mutation,
    )

    assert result.passed is False
    assert result.attempts == 2
    assert result.mutation_gap == 1
    assert len(calls) == 2


def test_property_strategy_passes():
    result = PostRepairVerificationLoop().verify(
        strategy=decision(VerificationStrategy.PROPERTY),
        run_standard=lambda: True,
        run_property=lambda: True,
    )

    assert result.passed is True
    assert result.attempts == 1


def test_property_strategy_retries_and_stops():
    result = PostRepairVerificationLoop(max_attempts=2).verify(
        strategy=decision(VerificationStrategy.PROPERTY),
        run_standard=lambda: True,
        run_property=lambda: False,
    )

    assert result.passed is False
    assert result.attempts == 2


def test_missing_property_verifier_fails_safely():
    result = PostRepairVerificationLoop().verify(
        strategy=decision(VerificationStrategy.PROPERTY),
        run_standard=lambda: True,
    )

    assert result.passed is False
    assert "no property verifier" in result.reasons[0]


def test_missing_mutation_verifier_fails_safely():
    result = PostRepairVerificationLoop().verify(
        strategy=decision(VerificationStrategy.MUTATION),
        run_standard=lambda: True,
    )

    assert result.passed is False
    assert "no mutation verifier" in result.reasons[0]


def test_loop_is_deterministic():
    first = PostRepairVerificationLoop(max_attempts=2).verify(
        strategy=decision(VerificationStrategy.STANDARD),
        run_standard=lambda: False,
    )
    second = PostRepairVerificationLoop(max_attempts=2).verify(
        strategy=decision(VerificationStrategy.STANDARD),
        run_standard=lambda: False,
    )

    assert first == second
