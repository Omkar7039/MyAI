import pytest

from experience.utility import ExperienceUtilityMeasurer


def test_positive_improvement_is_useful():
    result = ExperienceUtilityMeasurer().measure(
        baseline_score=50.0,
        observed_score=80.0,
    )

    assert result.useful is True
    assert result.baseline_score == 50.0
    assert result.observed_score == 80.0
    assert result.improvement == 30.0
    assert result.score == 60.0


def test_large_improvement_score_is_capped():
    result = ExperienceUtilityMeasurer().measure(
        baseline_score=10.0,
        observed_score=100.0,
    )

    assert result.useful is True
    assert result.improvement == 90.0
    assert result.score == 100.0


def test_zero_improvement_is_not_useful():
    result = ExperienceUtilityMeasurer().measure(
        baseline_score=70.0,
        observed_score=70.0,
    )

    assert result.useful is False
    assert result.improvement == 0.0
    assert result.score == 0.0


def test_negative_improvement_is_not_useful():
    result = ExperienceUtilityMeasurer().measure(
        baseline_score=80.0,
        observed_score=50.0,
    )

    assert result.useful is False
    assert result.improvement == -30.0
    assert result.score == 0.0


def test_unapplied_experience_is_not_useful():
    result = ExperienceUtilityMeasurer().measure(
        baseline_score=50.0,
        observed_score=90.0,
        applied=False,
    )

    assert result.useful is False
    assert result.score == 0.0
    assert result.improvement == 0.0
    assert result.reasons == (
        "experience was not applied",
    )


def test_minimal_improvement_is_detected():
    result = ExperienceUtilityMeasurer().measure(
        baseline_score=50.0,
        observed_score=50.5,
    )

    assert result.useful is True
    assert result.improvement == 0.5
    assert result.score == 1.0


def test_invalid_baseline_score_is_rejected():
    with pytest.raises(
        ValueError,
        match="baseline_score must be between 0 and 100",
    ):
        ExperienceUtilityMeasurer().measure(
            baseline_score=-1.0,
            observed_score=50.0,
        )


def test_invalid_observed_score_is_rejected():
    with pytest.raises(
        ValueError,
        match="observed_score must be between 0 and 100",
    ):
        ExperienceUtilityMeasurer().measure(
            baseline_score=50.0,
            observed_score=101.0,
        )


def test_boundary_scores_are_valid():
    result = ExperienceUtilityMeasurer().measure(
        baseline_score=0.0,
        observed_score=100.0,
    )

    assert result.improvement == 100.0
    assert result.score == 100.0


def test_measurement_is_deterministic():
    measurer = ExperienceUtilityMeasurer()

    first = measurer.measure(
        baseline_score=40.0,
        observed_score=85.0,
    )
    second = measurer.measure(
        baseline_score=40.0,
        observed_score=85.0,
    )

    assert first == second
