from memory.retriever import MemoryRetriever


def test_exact_symbol_ranks_first():
    retriever = MemoryRetriever()

    cases = [
        (
            "Orchestrator.handle",
            "function:Orchestrator.handle",
        ),
        (
            "DebugAgent.analyze",
            "function:DebugAgent.analyze",
        ),
        (
            "RepairAgent.repair_and_verify",
            "function:RepairAgent.repair_and_verify",
        ),
    ]

    for query, expected_kind in cases:
        results = retriever.search(query, top_k=5)

        assert results
        assert results[0].chunk.kind == expected_kind


def test_natural_language_retrieval_returns_results():
    retriever = MemoryRetriever()

    results = retriever.search(
        "mutation verification",
        top_k=5,
    )

    assert results
