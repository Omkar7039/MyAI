from project.change_aware_ranker import ChangeAwareRanker


def test_changed_files_are_prioritized():
    ranker = ChangeAwareRanker()

    ranked = ranker.rank(
        ['docs/readme.md', 'agents/repair.py', 'utils/helpers.py'],
        request='repair bug',
        changed_files=['utils/helpers.py'],
    )

    assert ranked[0].item == 'utils/helpers.py'
    assert ranked[0].score == 100
    assert 'recently changed' in ranked[0].reasons


def test_request_relevance_still_affects_unchanged_files():
    ranker = ChangeAwareRanker()

    ranked = ranker.rank(
        ['docs/readme.md', 'agents/repair.py', 'utils/helpers.py'],
        request='repair bug',
        changed_files=[],
    )

    assert ranked[0].item == 'agents/repair.py'


def test_ranking_is_deterministic():
    ranker = ChangeAwareRanker()

    first = ranker.rank(
        ['z.py', 'a.py', 'm.py'],
        request='database',
        changed_files=[],
    )
    second = ranker.rank(
        ['z.py', 'a.py', 'm.py'],
        request='database',
        changed_files=[],
    )

    assert first == second
    assert [item.item for item in first] == ['a.py', 'm.py', 'z.py']
