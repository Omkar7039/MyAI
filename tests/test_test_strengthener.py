from verification.test_strengthener import TestStrengthener
from verification.mutation_gap import MutationGapAssessment
from verification.weak_test_detector import WeakTestAssessment


def test_adds_boundary_case_to_single_assertion_suite():
    code = """
assert add(2, 3) == 5
"""

    result = TestStrengthener().strengthen(code)

    assert result.changed is True
    assert "assert add(0, 0) == 0" in result.strengthened_tests
    assert "added a zero-boundary case" in result.reasons


def test_adds_negative_case_when_only_positive_case_exists():
    code = """
assert add(2, 3) == 5
assert add(3, 2) == 5
"""

    result = TestStrengthener().strengthen(code)

    assert result.changed is True
    assert "assert add(-2, 2) == 0" in result.strengthened_tests


def test_mutation_gap_adds_targeted_case():
    code = """
assert add(2, 3) == 5
"""

    mutation = MutationGapAssessment(
        total_mutations=4,
        killed_mutations=3,
        survived_mutations=1,
        invalid_mutations=0,
        kill_rate=75.0,
        gap_rate=25.0,
        strong=False,
        reasons=("some mutations survived the current tests",),
    )

    result = TestStrengthener().strengthen(
        code,
        mutation_assessment=mutation,
    )

    assert result.changed is True
    assert "assert add(3, 0) == 3" in result.strengthened_tests
    assert any("mutation-gap-targeting case" in reason for reason in result.reasons)


def test_duplicate_assertions_trigger_new_coverage():
    code = """
assert add(2, 3) == 5
assert add(2, 3) == 5
"""

    weak = WeakTestAssessment(
        weak=True,
        score=40.0,
        assertion_count=2,
        duplicate_assertion_count=1,
        trivial_assertion_count=0,
        reasons=("test contains duplicate assertions",),
    )

    result = TestStrengthener().strengthen(
        code,
        weak_assessment=weak,
    )

    assert result.changed is True
    assert "assert add(1, 2) == 3" in result.strengthened_tests


def test_trivial_assertions_trigger_behavior_coverage():
    code = """
assert True
assert 1 == 1
"""

    weak = WeakTestAssessment(
        weak=True,
        score=0.0,
        assertion_count=2,
        duplicate_assertion_count=0,
        trivial_assertion_count=2,
        reasons=("test contains trivial assertions",),
    )

    result = TestStrengthener().strengthen(
        code,
        weak_assessment=weak,
    )

    assert result.changed is True
    assert "assert add(5, -5) == 0" in result.strengthened_tests


def test_existing_assertions_are_not_duplicated():
    code = """
assert add(2, 3) == 5
assert add(0, 0) == 0
"""

    result = TestStrengthener().strengthen(code)

    assert result.strengthened_tests.count(
        "assert add(0, 0) == 0"
    ) == 1


def test_no_changes_when_suite_needs_no_deterministic_strengthening():
    code = """
assert add(2, 3) == 5
assert add(-2, 2) == 0
assert add(0, 0) == 0
"""

    mutation = MutationGapAssessment(
        total_mutations=5,
        killed_mutations=5,
        survived_mutations=0,
        invalid_mutations=0,
        kill_rate=100.0,
        gap_rate=0.0,
        strong=True,
        reasons=("all valid mutations were killed",),
    )

    weak = WeakTestAssessment(
        weak=False,
        score=75.0,
        assertion_count=3,
        duplicate_assertion_count=0,
        trivial_assertion_count=0,
        reasons=(),
    )

    result = TestStrengthener().strengthen(
        code,
        weak_assessment=weak,
        mutation_assessment=mutation,
    )

    assert result.changed is False
    assert result.strengthened_tests == code
    assert result.added_tests == ()


def test_invalid_test_code_is_unchanged():
    code = """
assert add(2, 3) ==
"""

    result = TestStrengthener().strengthen(code)

    assert result.changed is False
    assert result.strengthened_tests == code
    assert result.added_tests == ()
    assert any("invalid test syntax" in reason for reason in result.reasons)


def test_strengthening_is_deterministic():
    code = """
assert add(2, 3) == 5
"""

    generator = TestStrengthener()

    first = generator.strengthen(code)
    second = generator.strengthen(code)

    assert first == second
