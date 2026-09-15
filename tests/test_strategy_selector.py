from verification.mutation_gap import MutationGapAssessment
from verification.strategy_selector import (
    VerificationStrategy,
    VerificationStrategySelector,
)
from verification.test_quality import TestQualityAssessment as QualityAssessment
from verification.weak_test_detector import WeakTestAssessment


def make_quality(valid=True, score=80.0):
    return QualityAssessment(
        valid=valid,
        assertion_count=4,
        statement_count=4,
        import_count=0,
        function_count=0,
        score=score,
        reasons=(),
    )


def make_weak(weak=False):
    return WeakTestAssessment(
        weak=weak,
        score=80.0 if not weak else 40.0,
        assertion_count=4 if not weak else 1,
        duplicate_assertion_count=0,
        trivial_assertion_count=0,
        reasons=(),
    )


def make_mutation(survived=0):
    total = 5
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


def test_invalid_tests_require_strengthening():
    decision = VerificationStrategySelector().select(
        quality=make_quality(valid=False, score=0.0),
        weak=make_weak(weak=True),
    )

    assert decision.strategy == VerificationStrategy.STRENGTHEN
    assert decision.priority == 100


def test_weak_tests_require_strengthening():
    decision = VerificationStrategySelector().select(
        quality=make_quality(),
        weak=make_weak(weak=True),
    )

    assert decision.strategy == VerificationStrategy.STRENGTHEN
    assert decision.priority == 90


def test_mutation_gap_selects_mutation_strategy():
    decision = VerificationStrategySelector().select(
        quality=make_quality(),
        weak=make_weak(),
        mutation=make_mutation(survived=2),
    )

    assert decision.strategy == VerificationStrategy.MUTATION
    assert decision.priority == 80
    assert "mutation gaps" in decision.reasons[0]


def test_property_operation_selects_property_strategy():
    decision = VerificationStrategySelector().select(
        quality=make_quality(),
        weak=make_weak(),
        mutation=make_mutation(),
        operation="sort",
    )

    assert decision.strategy == VerificationStrategy.PROPERTY
    assert decision.priority == 70


def test_unknown_operation_uses_standard_strategy():
    decision = VerificationStrategySelector().select(
        quality=make_quality(),
        weak=make_weak(),
        mutation=make_mutation(),
        operation="calculate",
    )

    assert decision.strategy == VerificationStrategy.STANDARD
    assert decision.priority == 50


def test_no_operation_uses_standard_strategy():
    decision = VerificationStrategySelector().select(
        quality=make_quality(),
        weak=make_weak(),
        mutation=make_mutation(),
    )

    assert decision.strategy == VerificationStrategy.STANDARD


def test_weak_tests_take_priority_over_mutation_gap():
    decision = VerificationStrategySelector().select(
        quality=make_quality(),
        weak=make_weak(weak=True),
        mutation=make_mutation(survived=3),
        operation="sort",
    )

    assert decision.strategy == VerificationStrategy.STRENGTHEN
    assert decision.priority == 90


def test_invalid_tests_take_priority_over_everything():
    decision = VerificationStrategySelector().select(
        quality=make_quality(valid=False, score=0.0),
        weak=make_weak(weak=True),
        mutation=make_mutation(survived=3),
        operation="sort",
    )

    assert decision.strategy == VerificationStrategy.STRENGTHEN
    assert decision.priority == 100


def test_strategy_selection_is_deterministic():
    selector = VerificationStrategySelector()

    first = selector.select(
        quality=make_quality(),
        weak=make_weak(),
        mutation=make_mutation(),
        operation="reverse",
    )
    second = selector.select(
        quality=make_quality(),
        weak=make_weak(),
        mutation=make_mutation(),
        operation="reverse",
    )

    assert first == second
