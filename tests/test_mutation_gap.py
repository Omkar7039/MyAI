from dataclasses import dataclass

from verification.mutation_gap import MutationGapAnalyzer


def test_all_mutations_killed_is_strong():
    result = MutationGapAnalyzer().assess(
        [True, True, True, True, True]
    )

    assert result.total_mutations == 5
    assert result.killed_mutations == 5
    assert result.survived_mutations == 0
    assert result.invalid_mutations == 0
    assert result.kill_rate == 100.0
    assert result.gap_rate == 0.0
    assert result.strong is True


def test_surviving_mutations_create_a_gap():
    result = MutationGapAnalyzer().assess(
        [True, True, False, True]
    )

    assert result.total_mutations == 4
    assert result.killed_mutations == 3
    assert result.survived_mutations == 1
    assert result.invalid_mutations == 0
    assert result.kill_rate == 75.0
    assert result.gap_rate == 25.0
    assert result.mutation_gap == 1
    assert result.strong is False


def test_mapping_outcomes_are_supported():
    result = MutationGapAnalyzer().assess(
        [
            {"killed": True},
            {"killed": False},
            {"killed": True},
        ]
    )

    assert result.killed_mutations == 2
    assert result.survived_mutations == 1
    assert result.invalid_mutations == 0


def test_status_outcomes_are_supported():
    result = MutationGapAnalyzer().assess(
        [
            {"status": "killed"},
            {"status": "survived"},
            {"status": "failed"},
            {"status": "passed"},
        ]
    )

    assert result.killed_mutations == 2
    assert result.survived_mutations == 2
    assert result.invalid_mutations == 0


@dataclass
class MutationOutcome:
    killed: bool


def test_object_outcomes_are_supported():
    result = MutationGapAnalyzer().assess(
        [
            MutationOutcome(killed=True),
            MutationOutcome(killed=False),
        ]
    )

    assert result.killed_mutations == 1
    assert result.survived_mutations == 1


def test_invalid_outcomes_are_tracked():
    result = MutationGapAnalyzer().assess(
        [True, False, {"status": "unknown"}, object()]
    )

    assert result.total_mutations == 4
    assert result.killed_mutations == 1
    assert result.survived_mutations == 1
    assert result.invalid_mutations == 2
    assert result.strong is False


def test_empty_results_are_safe():
    result = MutationGapAnalyzer().assess([])

    assert result.total_mutations == 0
    assert result.killed_mutations == 0
    assert result.survived_mutations == 0
    assert result.invalid_mutations == 0
    assert result.kill_rate == 0.0
    assert result.gap_rate == 0.0
    assert result.strong is False


def test_detection_is_deterministic():
    outcomes = [True, False, True, False]

    analyzer = MutationGapAnalyzer()

    first = analyzer.assess(outcomes)
    second = analyzer.assess(outcomes)

    assert first == second
