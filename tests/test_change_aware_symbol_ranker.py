from types import SimpleNamespace

from project.change_aware_symbol_ranker import ChangeAwareSymbolRanker


def test_recently_changed_file_prioritizes_its_symbol():
    symbols = [
        SimpleNamespace(
            name='helper',
            parent='Utils',
            file='utils.py',
            line=10,
        ),
        SimpleNamespace(
            name='repair',
            parent='RepairAgent',
            file='agents/repair.py',
            line=20,
        ),
    ]

    ranked = ChangeAwareSymbolRanker().rank(
        symbols,
        request='repair bug',
        changed_files=['utils.py'],
    )

    assert ranked[0].symbol.name == 'helper'
    assert ranked[0].score >= 100
    assert 'recently changed file' in ranked[0].reasons


def test_symbol_request_relevance_still_works():
    symbols = [
        SimpleNamespace(
            name='repair',
            parent='RepairAgent',
            file='agents/repair.py',
            line=20,
        ),
        SimpleNamespace(
            name='helper',
            parent='Utils',
            file='utils.py',
            line=10,
        ),
    ]

    ranked = ChangeAwareSymbolRanker().rank(
        symbols,
        request='RepairAgent repair bug',
        changed_files=[],
    )

    assert ranked[0].symbol.name == 'repair'
    assert ranked[0].score > 0


def test_symbol_ranking_is_deterministic():
    symbols = [
        SimpleNamespace(name='zeta', parent='', file='z.py', line=20),
        SimpleNamespace(name='alpha', parent='', file='a.py', line=10),
    ]

    ranker = ChangeAwareSymbolRanker()
    first = ranker.rank(symbols, request='database', changed_files=[])
    second = ranker.rank(symbols, request='database', changed_files=[])

    assert first == second
    assert first == []
