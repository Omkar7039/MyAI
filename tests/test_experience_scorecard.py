from experience.scorecard import ExperienceScorecardRunner


def test_experience_scorecard_is_perfect_for_current_contract():
    scorecard = ExperienceScorecardRunner().run()

    assert scorecard.retrieval == 100.0
    assert scorecard.applicability == 100.0
    assert scorecard.confidence == 100.0
    assert scorecard.contradiction == 100.0
    assert scorecard.consolidation == 100.0
    assert scorecard.project_scoping == 100.0
    assert scorecard.overall == 100.0
