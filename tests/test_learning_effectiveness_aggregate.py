import pytest

from experience.learning_effectiveness_aggregate import (
    LearningEffectivenessAggregator,
)


def test_empty_comparisons_are_safe():
    result = LearningEffectivenessAggregator().aggregate([])

    assert result.total_observations == 0
    assert result.improved_count == 0
    assert result.regression_count == 0
    assert result.neutral_count == 0
    assert result.improvement_rate == 0.0
    assert result.regression_rate == 0.0
    assert result.average_improvement == 0.0
    assert result.average_confidence == 0.0
    assert result.consistently_improving is False


def test_consistent_improvement_is_detected():
    result = LearningEffectivenessAggregator().aggregate(
        [
            (50.0, 80.0),
            (60.0, 85.0),
            (70.0, 90.0),
        ]
    )

    assert result.total_observations == 3
    assert result.improved_count == 3
    assert result.regression_count == 0
    assert result.neutral_count == 0
    assert result.improvement_rate == 100.0
    assert result.regression_rate == 0.0
    assert result.average_improvement == 25.0
    assert result.consistently_improving is True


def test_mixed_results_can_still_be_consistently_improving():
    result = LearningEffectivenessAggregator().aggregate(
        [
            (50.0, 80.0),
            (60.0, 85.0),
            (70.0, 90.0),
            (80.0, 70.0),
        ]
    )

    assert result.improved_count == 3
    assert result.regression_count == 1
    assert result.improvement_rate == 75.0
    assert result.regression_rate == 25.0
    assert result.consistently_improving is False


def test_regression_heavy_results_are_not_consistent():
    result = LearningEffectivenessAggregator().aggregate(
        [
            (80.0, 60.0),
            (70.0, 50.0),
            (90.0, 40.0),
        ]
    )

    assert result.improved_count == 0
    assert result.regression_count == 3
    assert result.regression_rate == 100.0
    assert result.consistently_improving is False


def test_neutral_results_are_tracked():
    result = LearningEffectivenessAggregator().aggregate(
        [
            (70.0, 70.0),
            (80.0, 80.0),
            (90.0, 90.0),
        ]
    )

    assert result.neutral_count == 3
    assert result.improvement_rate == 0.0
    assert result.regression_rate == 0.0
    assert result.average_improvement == 0.0
    assert result.consistently_improving is False


def test_three_observations_are_required():
    result = LearningEffectivenessAggregator().aggregate(
        [
            (50.0, 80.0),
            (60.0, 90.0),
        ]
    )

    assert result.improvement_rate == 100.0
    assert result.consistently_improving is False


def test_average_improvement_is_computed():
    result = LearningEffectivenessAggregator().aggregate(
        [
            (50.0, 70.0),
            (60.0, 90.0),
            (90.0, 80.0),
        ]
    )

    assert result.average_improvement == pytest.approx(
        13.333333333333334
    )


def test_average_confidence_is_computed():
    result = LearningEffectivenessAggregator().aggregate(
        [
            (50.0, 60.0),
            (50.0, 70.0),
        ]
    )

    assert result.average_confidence == pytest.approx(30.0)


def test_tuple_input_is_supported():
    result = LearningEffectivenessAggregator().aggregate(
        (
            (40.0, 60.0),
            (50.0, 70.0),
            (60.0, 80.0),
        )
    )

    assert result.total_observations == 3
    assert result.improved_count == 3


def test_boundary_for_regression_threshold():
    result = LearningEffectivenessAggregator().aggregate(
        [
            (50.0, 80.0),
            (60.0, 90.0),
            (70.0, 100.0),
            (80.0, 60.0),
            (90.0, 70.0),
            (100.0, 80.0),
            (50.0, 70.0),
            (60.0, 80.0),
            (70.0, 90.0),
            (80.0, 100.0),
        ]
    )

    assert result.total_observations == 10
    assert result.regression_rate == 30.0
    assert result.consistently_improving is False


def test_aggregation_is_deterministic():
    comparisons = [
        (50.0, 80.0),
        (60.0, 85.0),
        (70.0, 90.0),
    ]

    aggregator = LearningEffectivenessAggregator()

    first = aggregator.aggregate(comparisons)
    second = aggregator.aggregate(comparisons)

    assert first == second
